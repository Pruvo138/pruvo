#!/usr/bin/env python3
"""K308 KABUL BATARYASI — yedek dususu GORUNUR + KALICI + SAYILI mi?

VAKA (27 Agu 2026, ayni gun IKI push): pre-push birebir
`!! YEDEK alinamadi (rc=1, push DEVAM ediyor)` basti, push fail-open gecti ve
sebep hicbir kalici kayda dusmedi. Ayni turda ikinci gozlem: karantina
`ek/evler/pruvo-hasat/KIRLI-IZLENEN/parti-gunlugu.md` dosyasini ATLADI
(38.045 -> 8.129 B) ve atlama SAYIYLA beyan edilmedi.

BU BATARYA IKI KOLU OLCER:
  A) DUSUS GORUNUR: rc!=0 SESSIZ gecmez — `OLCULEMEDI=` + sebep ADIYLA basilir,
     ayri bir KALICI kayda duser, ve ARDISIK dusus sayaci tutulur.
  B) BOYUT DUSUSU BEYANSIZ GECMEZ: atlanan her dosya adi + eski/yeni bayt +
     fark ile basilir; toplam `BAYT_FARKI=` jetonu son satirda durur.

🔴 KENDI OLCUMUNU KUTSAMAMA: her kabul vakasi AYRICA bir MUTANTLA yargilanir.
Mutant HEDEF KOLU adiyla bozar; o vaka KIRMIZI yanmazsa vaka bos demektir
([[isci-yesil-tablo-ic-olcumu-bosaltir]]). KONTROL mutanti (zararsiz degisiklik)
YESIL kalmak ZORUNDA — yoksa batarya "her seye kirmizi yanan" alarma doner.

AGSIZ. Canli `~/.claude/cron/` duzlemine ve Drive'a YAZMAZ: her kosum kendi
gecici dizinini kurar ve sonunda SILER (uretim temizler).
"""
import filecmp
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import contextlib

BURASI = os.path.dirname(os.path.abspath(__file__))
YEDEKLE_KAYNAK = os.path.join(BURASI, "yedekle.py")
KANCA_KAYNAK = os.path.join(BURASI, "kancalar", "pre-push")

SAYAC = {"vaka": 0, "dusen": 0, "mutant": 0, "mutant_oldu": 0,
         "yama_tutmadi": 0, "kontrol_yesil": 0}
DUSEN_ADLAR = []
YAMA_TUTMAYAN = []


# ---------------------------------------------------------------- altyapi ----
def yukle(kaynak, ad):
    """yedekle.py'yi (ya da mutant kopyasini) TAZE yukler."""
    spec = importlib.util.spec_from_file_location(ad, kaynak)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def izole_et(mod, gecici):
    """Modulun kalici-kayit duzlemini GECICI dizine cevirir.

    🔴 Canli `~/.claude/cron/yedek-dusus.log` ve yerel kalp TEST TARAFINDAN
    KIRLETILEMEZ: sayaci test artirirsa canli ARDISIK degeri YALAN olur."""
    mod.DUSUS_KAYIT_LOG = os.path.join(gecici, "ops", "yedek-dusus.log")


def dusus_uret(mod, backup, adet=1, eski=38045, yeni=8129, sinif="bayt-dususu"):
    """Karantina listelerini GERCEK yapinin AYNISIYLA doldurur (taklit ozet YOK)."""
    del mod._KORUMA_KARANTINA[:]
    del mod._KORUMA_AYRINTI[:]
    for i in range(adet):
        varis = os.path.join(backup, "ek", "evler", "pruvo-hasat",
                             "KIRLI-IZLENEN", "parti-gunlugu-%d.md" % i)
        sebep = ("YEDEK REDDEDILDI: bayt olcusu ciddi dustu (%d -> %d); kanonik "
                 "DEGISMEDI (parti-gunlugu-%d.md)" % (eski, yeni, i))
        mod._KORUMA_KARANTINA.append((varis, sebep))
        mod._KORUMA_AYRINTI.append({"varis": varis, "kaynak": None, "sebep": sebep,
                                    "sinif": sinif, "eski": eski, "yeni": yeni})


def hukum_kos(mod, backup, adet=1, **kw):
    """Uretim fonksiyonunu cagirir, (rc, cikti) doner."""
    dusus_uret(mod, backup, adet=adet, **kw)
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = mod.karantina_hukmu_bas(backup)
    return rc, tampon.getvalue()


def temiz_kos(mod, backup):
    del mod._KORUMA_KARANTINA[:]
    del mod._KORUMA_AYRINTI[:]
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = mod.karantina_hukmu_bas(backup)
    return rc, tampon.getvalue()


def kalp_oku(mod):
    try:
        with open(mod._dusus_kalp_yerel(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                              # noqa: BLE001
        return {}


def kanca_suzgeci(kanca_metni, cikti):
    """pre-push YEDEK blogundaki SUZGECI cikarip ayni girdiyle kosturur.

    Kancanin kendi satirini kaynaktan okur — testin icine ikinci bir kopya
    YAZILMAZ ([[ad-iki-rolde-mutanti-golgeler]] / elle kopyalanan olcut sinifi)."""
    suzgec = None
    for satir in kanca_metni.splitlines():
        s = satir.strip()
        if s.startswith("| grep -E '^(KORUMA KARANTINASI"):
            suzgec = s.lstrip("|").strip().rstrip("\\").strip()
            break
        if s.startswith("' \"$pruvo_yedek_cikti\" | tail -3"):
            suzgec = "tail -3"
            break
        if s == "| tail -3":
            suzgec = "tail -3"
            break
    if suzgec is None:
        return None
    p = subprocess.run(["sh", "-c", suzgec], input=cikti,
                       capture_output=True, text=True)
    return p.stdout


# ------------------------------------------------------------------ vaka -----
def vaka(ad, kosul, detay=""):
    SAYAC["vaka"] += 1
    if kosul:
        print("  ok   %s" % ad)
    else:
        SAYAC["dusen"] += 1
        DUSEN_ADLAR.append(ad)
        print("  DUSTU %s   %s" % (ad, detay))
    return bool(kosul)


def kabul_kos(kaynak, kanca_metni, gecici, sessiz=False):
    """TUM kabul vakalarini kosar; doner: {vaka_adi: True/False}."""
    sonuc = {}
    mod = yukle(kaynak, "yedekle_kabul_%d" % len(os.listdir(gecici)))
    izole_et(mod, gecici)
    backup = os.path.join(gecici, "backup-v2")
    os.makedirs(os.path.join(backup, "ek", "evler", "pruvo-hasat",
                             "KIRLI-IZLENEN"), exist_ok=True)

    # --- B1: tek dosyalik dusus SAYIYLA basilir --------------------------
    rc, cikti = hukum_kos(mod, backup, adet=1)
    sonuc["B1-sayili-beyan"] = (
        rc == 1
        and "parti-gunlugu-0.md" in cikti
        and "eski=38045" in cikti and "yeni=8129" in cikti
        and "fark=-29916" in cikti
        and "BAYT_FARKI=-29916" in cikti)

    # --- A1: OLCULEMEDI + sebep ADIYLA + YEDEK=YARIM ---------------------
    sonuc["A1-olculemedi-jetonu"] = (
        "OLCULEMEDI=YEDEK_KARANTINA" in cikti
        and "SINIF=bayt-dususu" in cikti
        and "YEDEK=YARIM" in cikti)

    # --- A2: KALICI kayit gercekten DISKTE ------------------------------
    kalp = kalp_oku(mod)
    sonuc["A2-kalici-kayit"] = (
        os.path.isfile(mod._dusus_kalp_yerel())
        and kalp.get("ardisik") == 1
        and kalp.get("son_atlanan_adet") == 1
        and os.path.isfile(mod.DUSUS_KAYIT_LOG))

    # --- A3: ARDISIK sayac ARTAR, tavanda ESKALASYON ---------------------
    rc2, c2 = hukum_kos(mod, backup, adet=1)
    rc3, c3 = hukum_kos(mod, backup, adet=1)
    sonuc["A3-ardisik-sayac"] = ("ARDISIK=2" in c2 and "ARDISIK=3" in c3
                                 and kalp_oku(mod).get("ardisik") == 3)
    sonuc["A4-eskalasyon"] = ("ESKALASYON=YEDEK_ZINCIRI_KIRIK" not in c2
                              and "ESKALASYON=YEDEK_ZINCIRI_KIRIK" in c3)

    # --- A5: SAGLIKLI kosum sayaci SIFIRLAR, YEDEK=TAM ------------------
    rc0, c0 = temiz_kos(mod, backup)
    sonuc["A5-basari-sifirlar"] = (rc0 == 0 and "YEDEK=TAM" in c0
                                   and "ARDISIK=0" in c0
                                   and kalp_oku(mod).get("ardisik") == 0)

    # --- B2: COK dosyali dusus (bugunun SABAHKI vakasi: 4 dosya) ---------
    rc4, c4 = hukum_kos(mod, backup, adet=4, eski=10601, yeni=4746)
    dortu_de = all(("parti-gunlugu-%d.md" % i) in c4 for i in range(4))
    sonuc["B2-cok-dosya"] = (rc4 == 1 and dortu_de and "ATLANAN=4" in c4
                             and "BAYT_FARKI=-23420" in c4)

    # --- B3: KANCA SUZGECI hicbir atlamayi DUSURMEZ ----------------------
    suzulen = kanca_suzgeci(kanca_metni, c4)
    if suzulen is None:
        sonuc["B3-kanca-suzgeci"] = False
    else:
        sonuc["B3-kanca-suzgeci"] = (
            "KORUMA KARANTINASI: 4 dosya" in suzulen
            and all(("parti-gunlugu-%d.md" % i) in suzulen for i in range(4))
            and "YEDEK=YARIM" in suzulen)

    # --- B4: kayit sayisi dususu BAYT kovasina KARISMAZ ------------------
    rc5, c5 = hukum_kos(mod, backup, adet=1, eski=100, yeni=10,
                        sinif="kayit-dususu")
    sonuc["B4-kova-ayrimi"] = ("BAYT_FARKI=OLCULEMEDI" in c5
                               and "SINIF=kayit-dususu" in c5)

    if not sessiz:
        for ad in sorted(sonuc):
            vaka(ad, sonuc[ad])
    return sonuc


# --------------------------------------------------------------- mutantlar ---
MUTANTLAR = [
    ("M1-kayit-kolu-kaldirildi", "yedekle",
     "        kayit = dusus_kaydi_guncelle(backup, _KORUMA_AYRINTI, 1)",
     "        kayit = {}",
     ["A2-kalici-kayit", "A3-ardisik-sayac", "A4-eskalasyon"]),
    ("M2-sayac-artmiyor", "yedekle",
     '        kayit["ardisik"] = int(onceki.get("ardisik") or 0) + 1',
     '        kayit["ardisik"] = 1',
     ["A3-ardisik-sayac", "A4-eskalasyon"]),
    ("M3-sayilar-dusuruldu", "yedekle",
     '            olcu = "eski=%d -> yeni=%d, fark=%+d" % (eski, yeni, yeni - eski)',
     '            olcu = "olcu=VAR"',
     ["B1-sayili-beyan"]),
    ("M4-basari-sifirlamiyor", "yedekle",
     '        kayit["ardisik"] = 0',
     '        kayit["ardisik"] = int(onceki.get("ardisik") or 0)',
     ["A5-basari-sifirlar"]),
    ("M5-bayt-toplami-kor", "yedekle",
     "            bayt_farki = (bayt_farki or 0) + (yeni - eski)",
     "            bayt_farki = 0",
     ["B1-sayili-beyan", "B2-cok-dosya"]),
    ("M6-kanca-tail3-geri", "kanca",
     "      | grep -E '^(KORUMA KARANTINASI|  ATLANDI:|BEYAN UYARISI:|ESKALASYON=|YEDEK=)' \\",
     "      | tail -3",
     ["B3-kanca-suzgeci"]),
]

KONTROL = ("KONTROL-zararsiz", "yedekle",
           '    zaman = zaman if zaman is not None else time.time()',
           '    zaman = time.time() if zaman is None else zaman',
           [])


def mutant_kos(tanim, gecici):
    ad, hedef, capa, yeni, olmesi_gerekenler = tanim
    kok = os.path.join(gecici, "mutant-" + ad)
    os.makedirs(kok, exist_ok=True)
    m_yedekle = os.path.join(kok, "yedekle.py")
    shutil.copy2(YEDEKLE_KAYNAK, m_yedekle)
    # drive_yolu/veri_kok kardesleri yaninda olsun (yedekle.py import ediyor).
    for kardes in ("drive_yolu.py", "veri_kok.py"):
        k = os.path.join(BURASI, kardes)
        if os.path.exists(k):
            shutil.copy2(k, os.path.join(kok, kardes))
    kanca_metni = open(KANCA_KAYNAK, encoding="utf-8").read()

    if hedef == "yedekle":
        metin = open(m_yedekle, encoding="utf-8").read()
        if capa not in metin:
            SAYAC["yama_tutmadi"] += 1
            YAMA_TUTMAYAN.append(ad)
            print("  YAMA_TUTMADI %s — capa kaynakta YOK, bu eksen OLCULMUYOR" % ad)
            return
        open(m_yedekle, "w", encoding="utf-8").write(metin.replace(capa, yeni, 1))
    else:
        if capa not in kanca_metni:
            SAYAC["yama_tutmadi"] += 1
            YAMA_TUTMAYAN.append(ad)
            print("  YAMA_TUTMADI %s — capa kancada YOK, bu eksen OLCULMUYOR" % ad)
            return
        kanca_metni = kanca_metni.replace(capa, yeni, 1)

    kutu = os.path.join(kok, "kutu")
    os.makedirs(kutu, exist_ok=True)
    try:
        sonuc = kabul_kos(m_yedekle, kanca_metni, kutu, sessiz=True)
    except Exception as e:                                         # noqa: BLE001
        # Mutant PATLADIYSA kirmizi "hedef kol" yuzunden degil, cokme yuzundendir.
        print("  MUTANT_COKTU %s — %s (hedef-kol atfi YAPILAMAZ)" % (ad, e))
        SAYAC["mutant"] += 1
        return

    SAYAC["mutant"] += 1
    if not olmesi_gerekenler:                                       # KONTROL
        hepsi_yesil = all(sonuc.values())
        if hepsi_yesil:
            SAYAC["kontrol_yesil"] += 1
            print("  ok   %s (KONTROL YESIL — batarya alarm degil)" % ad)
        else:
            SAYAC["dusen"] += 1
            DUSEN_ADLAR.append(ad)
            print("  DUSTU %s — KONTROL mutanti kirmizi yakti: %s"
                  % (ad, [k for k, v in sonuc.items() if not v]))
        return

    olen = [v for v in olmesi_gerekenler if not sonuc.get(v, True)]
    yan_hasar = [k for k, v in sonuc.items()
                 if not v and k not in olmesi_gerekenler]
    if len(olen) == len(olmesi_gerekenler):
        SAYAC["mutant_oldu"] += 1
        print("  ok   %s -> HEDEF KOL kirmizi: %s%s"
              % (ad, ",".join(olen),
                 ("  (yan: %s)" % ",".join(yan_hasar)) if yan_hasar else ""))
    else:
        SAYAC["dusen"] += 1
        DUSEN_ADLAR.append(ad)
        print("  DUSTU %s — hedef kol OLMEDI (beklenen %s, olen %s)"
              % (ad, olmesi_gerekenler, olen))


# ------------------------------------------------------- GERI YUKLEME KANITI -
def geri_yukleme_kaniti(gecici):
    """🔴 YEDEGIN KANITI rc=0 DEGIL, GERI YUKLEMEDIR.

    Canli yedekten GERCEK bir dosya ayri bir dizine geri yuklenir ve canli
    aslıyla BAYT-BIREBIR (sha256 + filecmp shallow=False) karsilastirilir.
    Drive yoksa `OLCULEMEDI` doner — sessiz YESIL DONMEZ
    ([[olculemedi-bypass-degil-menzil-daraltmasi]])."""
    try:
        sys.path.insert(0, BURASI)
        import drive_yolu                                          # noqa: PLC0415
        pruvo = drive_yolu.pruvo_dizini(sessiz=True)
    except Exception as e:                                         # noqa: BLE001
        return ("OLCULEMEDI", "drive_yolu patladi: %s" % e)
    if not pruvo:
        return ("OLCULEMEDI", "Drive mount cozulemedi")
    backup = os.path.join(pruvo, "yedekle_kok_adi")
    yedekle = yukle(YEDEKLE_KAYNAK, "yedekle_geri")
    backup = os.path.join(pruvo, yedekle.YEDEK_KOK_ADI)
    if not os.path.isdir(backup):
        return ("OLCULEMEDI", "backup koku yok: %s" % backup)

    kok = yedekle.ROOT
    adaylar = []
    for ad in sorted(os.listdir(backup)):
        y = os.path.join(backup, ad)
        c = os.path.join(kok, ad)
        if (os.path.isfile(y) and os.path.isfile(c) and "." in ad
                and os.path.getsize(y) > 0 and ".2026" not in ad):
            adaylar.append((ad, y, c))
    if not adaylar:
        return ("OLCULEMEDI", "yedek<->canli eslesen dosya bulunamadi")

    hedef = os.path.join(gecici, "geri-yukleme")
    os.makedirs(hedef, exist_ok=True)
    esit, farkli = [], []
    for ad, y, c in adaylar:
        geri = os.path.join(hedef, ad)
        shutil.copy2(y, geri)                       # <- GERCEK geri yukleme
        h_geri = hashlib.sha256(open(geri, "rb").read()).hexdigest()
        h_canli = hashlib.sha256(open(c, "rb").read()).hexdigest()
        if h_geri == h_canli and filecmp.cmp(geri, c, shallow=False):
            esit.append((ad, os.path.getsize(geri), h_geri))
        else:
            farkli.append((ad, os.path.getsize(geri), os.path.getsize(c)))
    if not esit:
        return ("DUSTU", "hicbir dosya bayt-birebir degil; farklilar=%s" % farkli)
    ad, boyut, sha = esit[0]
    return ("GECTI", "aday=%d bayt_birebir=%d ornek=%s boyut=%d sha256=%s"
            % (len(adaylar), len(esit), ad, boyut, sha[:16]))


# ------------------------------------------------------------------- main ----
def main():
    print("K308 KABUL — yedek dususu GORUNUR + KALICI + SAYILI mi?")
    gecici = tempfile.mkdtemp(prefix="k308-kabul-")
    try:
        kanca_metni = open(KANCA_KAYNAK, encoding="utf-8").read()

        print("[1/3] TABAN kabul vakalari")
        taban_kutu = os.path.join(gecici, "taban")
        os.makedirs(taban_kutu, exist_ok=True)
        taban = kabul_kos(YEDEKLE_KAYNAK, kanca_metni, taban_kutu)

        print("[2/3] MUTANTLAR (hedef-kol atifli) + KONTROL")
        for m in MUTANTLAR:
            mutant_kos(m, gecici)
        mutant_kos(KONTROL, gecici)

        print("[3/3] GERI YUKLEME KANITI (bayt-birebir)")
        geri_hukum, geri_detay = geri_yukleme_kaniti(gecici)
        print("  GERI_YUKLEME=%s   %s" % (geri_hukum, geri_detay))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        # 🔴 URETEN TEMIZLER: gecici agac her kosumda silinir.
        artik = os.path.isdir(gecici)

    hedefli = len([m for m in MUTANTLAR if m[4]])
    print("")
    print("VAKA=%d DUSEN=%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d "
          "YAMA_TUTMADI=%d KONTROL_YESIL=%d GERI_YUKLEME=%s ARTIK_DIZIN=%s"
          % (SAYAC["vaka"], SAYAC["dusen"], SAYAC["mutant_oldu"], hedefli,
             SAYAC["mutant_oldu"], hedefli, SAYAC["yama_tutmadi"],
             SAYAC["kontrol_yesil"], geri_hukum, "VAR" if artik else "YOK"))
    if DUSEN_ADLAR:
        print("DUSEN_ADLAR=%s" % ",".join(DUSEN_ADLAR))
    if YAMA_TUTMAYAN:
        print("YAMA_TUTMAYAN=%s" % ",".join(YAMA_TUTMAYAN))

    kirmizi = (SAYAC["dusen"] or SAYAC["yama_tutmadi"]
               or SAYAC["mutant_oldu"] != hedefli
               or SAYAC["kontrol_yesil"] != 1
               or geri_hukum != "GECTI"
               or artik)
    print("HUKUM=%s" % ("KIRMIZI" if kirmizi else "YESIL"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
