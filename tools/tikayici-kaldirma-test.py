#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/tikayici-kaldirma-kabul.py — 11 EYL 2026 OKAN EMRI ("tum tikayicilari kaldir")
DILIM 2'nin KABUL NOBETCISI: mimar kapilarindan REDDETME YETKISI kalkti mi, TESHIS
kaldi mi, ve komsu nobetciler AYNEN RED mi veriyor?

=== NE OLCER (dort kalem) =====================================================
KALEM 1  `mimar-icra-kapisi.py`   — olcum/tarama komutlari + python3/node ARAC kosumu
                                    ANA oturumda da GECER; rol + komut sinifi stderr'de.
KALEM 2  `mimar-kod-kilidi.py`    — .py/.sh yazimi GECER ve SAYILIR (MIMAR_KOD_YAZDI);
                                    urunler.json / CEKIRDEK / kapi adi AYNEN RED.
KALEM 3  `komut-stili-kapisi.py`  — REDDETMEZ, UYARIR; tirnak ICINDEKI `>` komut sayilmaz
                                    ama cift tirnaktaki `$` GENISLER (POSIX).
KALEM 4  defter/kutu/hafiza kotasi — tavanlar 500; BAYT ekseni HUKUM VERMEZ, RAPOR eder;
                                    `KORUMALI ... DEGIL` olumsuzlamasi veto URETMEZ.

=== MUTASYON DISIPLINI ========================================================
🔴 MUTANT CANLI GOVDEDE YASAMAZ ([[mutant-canli-govdede-yasamaz]]): her mutant IZOLE bir
   kopyaya uygulanir (tempdir + tools/*.py kopyasi). Canli dosyaya ASLA yazilmaz.
🔴 CAPA DOGRULANIR ([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]): yama
   uygulanmadiysa vaka YESIL SAYILMAZ, `CAPA_YOK` ile KIRMIZI yanar. Aksi halde capa
   bayatladiginda batarya sessizce 0 mutant kosturur — bu repoda olculmus ariza.
🔴 KONTROL VAKASI SART ([[mutant-kopyasi-cokerse-izin-okunur]]): yamasiz kopya YESIL
   olmali; olmazsa olculen sey mutant degil KOPYANIN KENDISIDIR.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")

ANA_DAMGA = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/kabul.jsonl"

sonuclar = []   # (ad, gecti, olculen, beklenen, not)


def kaydet(ad, gecti, olculen, beklenen, not_=""):
    sonuclar.append((ad, gecti, str(olculen), str(beklenen), not_))


# ---------------------------------------------------------------------------
# IZOLE KOPYA + CAPA DOGRULAMALI MUTASYON
# ---------------------------------------------------------------------------
def izole_kopya():
    """tools/*.py'yi gecici bir dizine kopyalar; (dizin, tools_yolu) doner.

    Yalniz .py kopyalanir: kapilar birbirini ADLA import eder (mimar_kimlik,
    serbest_cagrilar), veri dosyalarina ihtiyac YOKTUR ve tam kopya yavas olurdu.
    """
    d = tempfile.mkdtemp(prefix="tikayici-kabul-")
    ht = os.path.join(d, "tools")
    os.makedirs(ht)
    for ad in os.listdir(TOOLS):
        if ad.endswith(".py"):
            shutil.copy2(os.path.join(TOOLS, ad), os.path.join(ht, ad))
    return d, ht


def yama(tools_yolu, dosya, capa, yerine, etiket):
    """Izole kopyada `capa` -> `yerine`. CAPA YOKSA (None, sebep) doner.

    Donus: (True, "") uygulandi · (False, sebep) uygulanmadi.
    """
    yol = os.path.join(tools_yolu, dosya)
    try:
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        return False, "kopya okunamadi: %s" % e
    if capa not in metin:
        return False, "CAPA_YOK (%s icinde bulunamadi) etiket=%s" % (dosya, etiket)
    sayi = metin.count(capa)
    metin = metin.replace(capa, yerine)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return True, "capa x%d" % sayi


# ---------------------------------------------------------------------------
# KAPI CAGRISI (PreToolUse)
# ---------------------------------------------------------------------------
def kapiya_ver(kapi_yolu, girdi):
    p = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(girdi),
                       capture_output=True, text=True)
    s = (p.stdout or "").strip()
    karar = None
    if s:
        try:
            karar = (json.loads(s).get("hookSpecificOutput") or {}).get(
                "permissionDecision")
        except Exception:
            karar = "COZULEMEDI"
    return ("RED" if karar == "deny" else "GECER"), p.stderr, p.returncode


def bash_girdi(komut, damga=ANA_DAMGA):
    return {"tool_name": "Bash", "tool_input": {"command": komut},
            "cwd": KOK, "transcript_path": damga, "session_id": "kabul-bataryasi"}


def yaz_girdi(yol, damga=ANA_DAMGA):
    return {"tool_name": "Write", "tool_input": {"file_path": yol, "content": "x\n"},
            "cwd": KOK, "transcript_path": damga, "session_id": "kabul-bataryasi"}


# ===========================================================================
# KALEM 1 — MIMAR ICRA KAPISI
# ===========================================================================
K1_OLCUM_CAPA = """        if ad in OLCUM_KOMUTLARI:
            iz_bas("OLCUM-SERBEST rol=" + ("CIP" if cip else "ANA") +
                   " sinif=OLCUM/TARAMA komut=" + ad)"""

K1_RED_GERI = """        if ad in OLCUM_KOMUTLARI and not cip:
            reddet("olcum / dosya-tarama komutu (" + ad + ").")"""

K1_TESHIS_SUSTU = """        if ad in OLCUM_KOMUTLARI:
            pass"""


def kalem1(tools_yolu, etiket):
    """(sed GECER mi, teshis VAR mi)"""
    kapi = os.path.join(tools_yolu, "mimar-icra-kapisi.py")
    karar, err, rc = kapiya_ver(kapi, bash_girdi("sed -n '1,5p' DEVAM.md"))
    teshis = "OLCUM-SERBEST" in err and "rol=ANA" in err and "komut=sed" in err
    return karar, teshis, rc


def kalem1_kos():
    # --- TABAN: canli govde (yamasiz) ---
    karar, teshis, rc = kalem1(TOOLS, "TABAN")
    kaydet("K1 TABAN  sed ANA -> GECER", karar == "GECER" and rc == 0, karar, "GECER")
    kaydet("K1 TABAN  teshis stderr'de (rol+sinif+komut)", teshis, teshis, True)

    # --- KONTROL: izole kopya yamasiz da YESIL olmali ---
    d, ht = izole_kopya()
    try:
        karar, teshis, rc = kalem1(ht, "KONTROL")
        kaydet("K1 KONTROL izole kopya yamasiz -> GECER",
               karar == "GECER" and teshis, karar, "GECER")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 1a: REDDETME YOLU GERI KONUR -> vaka KIRMIZI olmali ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-icra-kapisi.py", K1_OLCUM_CAPA, K1_RED_GERI,
                        "K1_RED_GERI")
        if not ok:
            kaydet("K1 MUTANT M1a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _t, _rc = kalem1(ht, "M1a")
            kaydet("K1 MUTANT M1a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 1b: TESHIS SUSTURULUR -> vaka KIRMIZI olmali ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-icra-kapisi.py", K1_OLCUM_CAPA, K1_TESHIS_SUSTU,
                        "K1_TESHIS_SUSTU")
        if not ok:
            kaydet("K1 MUTANT M1b TESHIS-SUSTU", False, notu, "capa uygulanmali")
        else:
            karar, teshis, _rc = kalem1(ht, "M1b")
            # Karar GECER kalir ama TESHIS KAYBOLUR -> vaka KIRMIZI.
            kaydet("K1 MUTANT M1b TESHIS-SUSTU -> teshis vakasi KIRMIZI",
                   teshis is False, "teshis=%s" % teshis, "teshis=False", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- KAPSAM: acilmamasi gerekenler AYNEN RED ---
    for ad, komut in (("python3 -c satir-ici kod", "python3 -c 'import os'"),
                      ("repo DISI betik", "python3 /private/tmp/x/kotu.py"),
                      ("curl (emirde anilmadi)", "curl -s https://pruvo3d.com")):
        karar, _e, _rc = kapiya_ver(os.path.join(TOOLS, "mimar-icra-kapisi.py"),
                                    bash_girdi(komut))
        kaydet("K1 KAPSAM  %s -> RED KALIR" % ad, karar == "RED", karar, "RED")


# ===========================================================================
# KALEM 2 — MIMAR KOD-KILIDI
# ===========================================================================
K2_CAPA = """if fp.lower().endswith(ICRA_UZANTILARI):
    _kod_yazimi_kaydet(girdi, fp)
    iz_bas("MIMAR-KOD-YAZDI " + fp)
    sys.exit(0)"""

K2_RED_GERI = """if fp.lower().endswith(ICRA_UZANTILARI):
    reddet("MIMAR KOD-KILIDI — CALISTIRILABILIR BETIK YAZARLIGI YASAK.")"""

K2_SAYAC_SUSTU = """if fp.lower().endswith(ICRA_UZANTILARI):
    iz_bas("MIMAR-KOD-YAZDI " + fp)
    sys.exit(0)"""

K2_PY = "/private/tmp/claude-501/x/scratchpad/kabul-olcum.py"


def kalem2_yaz(tools_yolu, oturum):
    kapi = os.path.join(tools_yolu, "mimar-kod-kilidi.py")
    g = yaz_girdi(K2_PY)
    g["session_id"] = oturum
    return kapiya_ver(kapi, g)


def kalem2_rapor(tools_yolu, oturum):
    kapi = os.path.join(tools_yolu, "mimar-kod-kilidi.py")
    p = subprocess.run([sys.executable, kapi, "--rapor", "--oturum", oturum,
                        "--temizle"], capture_output=True, text=True)
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("MIMAR_KOD_YAZDI="):
            try:
                return int(satir.split("=", 1)[1].split()[0])
            except (ValueError, IndexError):
                return None
    return None


def kalem2_kos():
    # --- TABAN ---
    karar, err, rc = kalem2_yaz(TOOLS, "kabul-taban")
    kaydet("K2 TABAN  scratchpad .py -> GECER", karar == "GECER" and rc == 0,
           karar, "GECER")
    kaydet("K2 TABAN  teshis MIMAR-KOD-YAZDI stderr'de", "MIMAR-KOD-YAZDI" in err,
           "MIMAR-KOD-YAZDI" in err, True)
    n = kalem2_rapor(TOOLS, "kabul-taban")
    kaydet("K2 TABAN  MIMAR_KOD_YAZDI=1 dosya", n == 1, n, 1)

    # --- KONTROL ---
    d, ht = izole_kopya()
    try:
        karar, err, _rc = kalem2_yaz(ht, "kabul-kontrol")
        kalem2_rapor(ht, "kabul-kontrol")
        kaydet("K2 KONTROL izole kopya yamasiz -> GECER", karar == "GECER",
               karar, "GECER")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 2a: REDDETME GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-kod-kilidi.py", K2_CAPA, K2_RED_GERI, "K2_RED_GERI")
        if not ok:
            kaydet("K2 MUTANT M2a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _e, _rc = kalem2_yaz(ht, "kabul-m2a")
            kaydet("K2 MUTANT M2a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 2b: SAYAC SUSTURULUR (gorunurluk olur) ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-kod-kilidi.py", K2_CAPA, K2_SAYAC_SUSTU,
                        "K2_SAYAC_SUSTU")
        if not ok:
            kaydet("K2 MUTANT M2b SAYAC-SUSTU", False, notu, "capa uygulanmali")
        else:
            kalem2_yaz(ht, "kabul-m2b")
            n = kalem2_rapor(ht, "kabul-m2b")
            kaydet("K2 MUTANT M2b SAYAC-SUSTU -> MIMAR_KOD_YAZDI=0 (vaka KIRMIZI)",
                   n == 0, n, 0, notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- NOBETCILER: AYNEN RED ---
    # 🔴 CAPA ANA CHECKOUT'TUR, `KOK` DEGIL — OLCULDU (11 Eyl, bu batarya kendi
    # kusurunu yakaladi): vakalari `os.path.join(KOK, ...)` ile yazdigimda DORDU
    # GECER dondu. Sebep REGRESYON DEGIL, YANLIS CAPA: kilidin 2. adimi
    # (`worktree_ici`) worktree yollarini ZATEN muaf tutar ve bu davranis 20 Tem'den
    # beri BOYLE ("worktree kopyalari serbesttir" — kaynaktaki vaka 72). Kilit
    # yalnizca ANA CHECKOUT yollarini korur (`REPO_ONEKI` suzgeci, adim 6), o yuzden
    # nobetci vakasi ORAYA nisanlanir ([[spec-mutlak-yol-yanlis-agaci-olcer]] sinifi).
    ANA = "/Users/okan/dev/pruvo/"
    kapi = os.path.join(TOOLS, "mimar-kod-kilidi.py")
    for ad, yol in (
            ("urunler.json", ANA + "urunler.json"),
            (".urun-kaynaklari.json", ANA + ".urun-kaynaklari.json"),
            ("CEKIRDEK urunler-guard.py", ANA + "tools/urunler-guard.py"),
            ("kapi ADI kalkani", ANA + "baska/mimar-icra-kapisi.py"),
            ("index.html", ANA + "index.html"),
            ("settings.json", ANA + ".claude/settings.json")):
        karar, _e, _rc = kapiya_ver(kapi, yaz_girdi(yol))
        kaydet("K2 NOBETCI %s -> RED KALIR" % ad, karar == "RED", karar, "RED")

    # --- WORKTREE MUAFIYETI: OLCULUR, KAZA OLMAZ ---
    # Bu muafiyet ONCEDEN VARDI ve bu is onu DEGISTIRMEDI. Vaka olarak yazilir ki
    # bir gun sessizce kapanirsa (ya da yanlislikla ANA checkout'a genislerse)
    # batarya ADIYLA yansin.
    karar, _e, _rc = kapiya_ver(kapi, yaz_girdi(os.path.join(KOK, "urunler.json")))
    kaydet("K2 MUAFIYET worktree urunler.json -> GECER (onceden de boyleydi)",
           karar == "GECER", karar, "GECER")


# ===========================================================================
# KALEM 3 — KOMUT STILI KAPISI
# ===========================================================================
K3_CAPA = "bulunan = [ad for desen, ad, sinif in YASAK if re.search(desen, TARAMA[sinif])]"
K3_TIRNAK_KOR = "bulunan = [ad for desen, ad, sinif in YASAK if re.search(desen, komut)]"
K3_RED_CAPA = """if bulunan:
    sys.stderr.write("""
K3_RED_GERI = """if bulunan:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": "KOMUT STILI KAPISI: " + ", ".join(bulunan)}},
        ensure_ascii=False))
    sys.exit(0)
if bulunan:
    sys.stderr.write("""

K3_METIN = 'git commit -m "kutu 250 -> 500 oldu"'
K3_GERCEK = "python3 tools/durum.py > /tmp/x.txt"
K3_DOLAR = 'echo "x=$?"'


def k3(tools_yolu, komut):
    kapi = os.path.join(tools_yolu, "komut-stili-kapisi.py")
    karar, err, rc = kapiya_ver(kapi, bash_girdi(komut))
    return karar, ("KOMUT STILI UYARISI" in err), rc


def kalem3_kos():
    # --- TABAN ---
    karar, uyari, rc = k3(TOOLS, K3_METIN)
    kaydet("K3 TABAN  metin ici '->' -> GECER, UYARI YOK",
           karar == "GECER" and not uyari and rc == 0,
           "%s/uyari=%s" % (karar, uyari), "GECER/uyari=False")
    karar, uyari, _rc = k3(TOOLS, K3_GERCEK)
    kaydet("K3 TABAN  GERCEK yonlendirme -> GECER ama UYARI VAR",
           karar == "GECER" and uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=True")
    karar, uyari, _rc = k3(TOOLS, K3_DOLAR)
    kaydet("K3 TABAN  cift tirnakta $ GENISLER -> GECER + UYARI (POSIX)",
           karar == "GECER" and uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=True")
    karar, uyari, _rc = k3(TOOLS, "ls /Users/okan/dev/pruvo")
    kaydet("K3 TABAN  duz komut -> GECER, UYARI YOK",
           karar == "GECER" and not uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=False")

    # --- TIRNAK MASKELEME KENAR VAKALARI ---
    # 🔴 Maskeleme bir AYRISTIRICIDIR; ayristiricilarin arizasi kenarlarda dogar.
    # Her vaka POSIX kabuk semantigine gore YAZILDI, tahmine gore DEGIL.
    for komut, uyari_bekle, not_ in (
            # tek tirnak: `$` GENISLEMEZ -> uyari YOK
            ("echo 'fiyat $HOME degil metin'", False, "tek tirnakta $ literal"),
            # cift tirnak: `$` GENISLER -> uyari VAR
            ('echo "ev $HOME"', True, "cift tirnakta $ genisler"),
            # kacisli $ : genislemez -> uyari YOK
            ('echo "fiyat \\$500"', False, "kacisli \\$ genislemez"),
            # tek tirnak icinde `>` : literal -> uyari YOK
            ("git commit -m 'A > B tasindi'", False, "tek tirnakta > literal"),
            # cift tirnak icinde `>` : literal -> uyari YOK
            ('git commit -m "A > B tasindi"', False, "cift tirnakta > literal"),
            # tirnak DISINDA gercek yonlendirme -> uyari VAR
            ("ls > /tmp/x.txt", True, "tirnak disi gercek yonlendirme"),
            # KAPANMAMIS tirnak: kalan kisim metin sayilir (fail-safe) -> uyari YOK
            ('echo "kapanmamis > metin', False, "kapanmamis tirnak fail-safe"),
            # tirnakli metinden SONRA gercek yonlendirme -> uyari VAR
            ('echo "metin > degil" > /tmp/x.txt', True, "metin sonrasi gercek >"),
    ):
        karar, uyari, _rc = k3(TOOLS, komut)
        kaydet("K3 TIRNAK  %s" % not_,
               karar == "GECER" and uyari == uyari_bekle,
               "%s/uyari=%s" % (karar, uyari),
               "GECER/uyari=%s" % uyari_bekle)

    # --- KONTROL ---
    d, ht = izole_kopya()
    try:
        karar, uyari, _rc = k3(ht, K3_METIN)
        kaydet("K3 KONTROL izole kopya yamasiz -> GECER/uyari=False",
               karar == "GECER" and not uyari, "%s/uyari=%s" % (karar, uyari),
               "GECER/uyari=False")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 3a: REDDETME GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "komut-stili-kapisi.py", K3_RED_CAPA, K3_RED_GERI,
                        "K3_RED_GERI")
        if not ok:
            kaydet("K3 MUTANT M3a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _u, _rc = k3(ht, K3_GERCEK)
            kaydet("K3 MUTANT M3a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 3b: TIRNAK DUYARLILIGI KOR EDILIR ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "komut-stili-kapisi.py", K3_CAPA, K3_TIRNAK_KOR,
                        "K3_TIRNAK_KOR")
        if not ok:
            kaydet("K3 MUTANT M3b TIRNAK-KOR", False, notu, "capa uygulanmali")
        else:
            karar, uyari, _rc = k3(ht, K3_METIN)
            kaydet("K3 MUTANT M3b TIRNAK-KOR -> metin vakasi UYARI URETIR (KIRMIZI)",
                   uyari is True, "uyari=%s" % uyari, "uyari=True", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# KALEM 4 — DEFTER / KUTU / HAFIZA KOTASI
# ===========================================================================
def modul_yukle(ad, yol):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def k4_taban_olc(tools_yolu):
    """(TAVAN_SATIR, kutu VARSAYILAN_TAVAN, hafiza SATIR, bayt_hukum)"""
    t = modul_yukle("k4_taban_%d" % abs(hash(tools_yolu)),
                    os.path.join(tools_yolu, "defter-kota-taban.py"))
    ka = modul_yukle("k4_kutu_%d" % abs(hash(tools_yolu)),
                     os.path.join(tools_yolu, "kutu-arsivle.py"))
    ha = modul_yukle("k4_haf_%d" % abs(hash(tools_yolu)),
                     os.path.join(tools_yolu, "hafiza-indeks-arsivle.py"))
    return t, ka, ha


def kalem4_kos():
    t, ka, ha = k4_taban_olc(TOOLS)

    # --- TABAN: SAYILAR ---
    kaydet("K4 TABAN  DEVAM.md TAVAN_SATIR=500", t.TAVAN_SATIR == 500,
           t.TAVAN_SATIR, 500)
    kaydet("K4 TABAN  kutu VARSAYILAN_TAVAN=500", ka.VARSAYILAN_TAVAN == 500,
           ka.VARSAYILAN_TAVAN, 500)
    kaydet("K4 TABAN  hafiza VARSAYILAN_TAVAN_SATIR=500",
           ha.VARSAYILAN_TAVAN_SATIR == 500, ha.VARSAYILAN_TAVAN_SATIR, 500)

    # --- TABAN: BAYT EKSENI HUKUM VERMEZ ---
    kaydet("K4 TABAN  BAYT_HUKUM_VERIR=False", t.BAYT_HUKUM_VERIR is False,
           t.BAYT_HUKUM_VERIR, False)
    asi, eksen, _s, _b = t.tavan_asi_mi(100, t.TAVAN_BAYT + 5000)
    kaydet("K4 TABAN  satir ALTINDA + bayt USTUNDE -> ASMADI, eksen BAYT_RAPOR",
           asi is False and eksen == "BAYT_RAPOR", "asi=%s eksen=%s" % (asi, eksen),
           "asi=False eksen=BAYT_RAPOR")
    asi, eksen, _s, _b = t.tavan_asi_mi(t.TAVAN_SATIR + 1, 100)
    kaydet("K4 TABAN  satir USTUNDE -> ASTI, eksen SATIR (kapi HALA durdurur)",
           asi is True and eksen == "SATIR", "asi=%s eksen=%s" % (asi, eksen),
           "asi=True eksen=SATIR")

    # --- TABAN: HAFIZA ekseni de bayta HUKUM VERMEZ ---
    dk = modul_yukle("k4_kapi", os.path.join(TOOLS, "defter-kota-kapisi.py"))
    hal = dk.hafiza_hali(True, True, True, 100, 99999, 500, 16384)
    kaydet("K4 TABAN  hafiza: bayt USTUNDE + satir ALTINDA -> HAFIZA_YESIL",
           hal == dk.HAFIZA_YESIL, hal, dk.HAFIZA_YESIL)
    hal = dk.hafiza_hali(True, True, True, 501, 100, 500, 16384)
    kaydet("K4 TABAN  hafiza: satir USTUNDE -> HAFIZA_ASILDI",
           hal == dk.HAFIZA_ASILDI, hal, dk.HAFIZA_ASILDI)

    # --- TABAN: KORUMALI iki yonlu esleme ---
    satirlar = [
        "## 2026-09-10 — BaBa (KORUMALI: BaBa kapatir) **A**", "govde",
        "## 2026-09-10 — BaBa (bilgi, KORUMALI değil) **B**", "govde",
        "## 2026-09-10 — BaBa (KORUMALI DEGIL) **C**", "govde",
        "## 2026-09-10 — BaBa (duz baslik) **D**", "govde KORUMALI kelimesi",
    ]
    baslar = ka.blok_baslari(satirlar)
    bulgu, govde, dustu, olumsuz = ka.korumali_etiketli_bloklar(satirlar, baslar)
    kaydet("K4 TABAN  KORUMALI veto=1 (yalniz gercek etiket)", len(bulgu) == 1,
           len(bulgu), 1)
    kaydet("K4 TABAN  ETIKET_OLUMSUZ=2 ('değil' + 'DEGIL', TR-guvenli)",
           len(olumsuz) == 2, len(olumsuz), 2)
    kaydet("K4 TABAN  govde anmasi=1 (BASLIKTA degil -> veto YOK)", govde == 1,
           govde, 1)
    kaydet("K4 TABAN  etiket_olumsuzlandi_mi('... KORUMALI değil)') True",
           ka.etiket_olumsuzlandi_mi("x (bilgi, KORUMALI değil) y") is True,
           True, True)
    kaydet("K4 TABAN  NON-GROWTH: duz 'KORUMALI:' etiketi olumsuz SAYILMAZ",
           ka.etiket_olumsuzlandi_mi("x (KORUMALI: BaBa kapatir) y") is False,
           False, False)

    # --- MUTANT 4a: BAYT HUKMU GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "defter-kota-taban.py", "BAYT_HUKUM_VERIR = False",
                        "BAYT_HUKUM_VERIR = True", "K4_BAYT_HUKUM_GERI")
        if not ok:
            kaydet("K4 MUTANT M4a BAYT-HUKUM-GERI", False, notu, "capa uygulanmali")
        else:
            tm = modul_yukle("k4_m4a", os.path.join(ht, "defter-kota-taban.py"))
            asi, eksen, _s, _b = tm.tavan_asi_mi(100, tm.TAVAN_BAYT + 5000)
            kaydet("K4 MUTANT M4a BAYT-HUKUM-GERI -> bayt vakasi KIRMIZI (asi=True)",
                   asi is True and eksen == "BAYT", "asi=%s eksen=%s" % (asi, eksen),
                   "asi=True eksen=BAYT", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 4b: KUTU TAVANI 250'YE GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "kutu-arsivle.py", "VARSAYILAN_TAVAN = 500",
                        "VARSAYILAN_TAVAN = 250", "K4_TAVAN_GERI")
        if not ok:
            kaydet("K4 MUTANT M4b TAVAN-GERI", False, notu, "capa uygulanmali")
        else:
            kam = modul_yukle("k4_m4b", os.path.join(ht, "kutu-arsivle.py"))
            hal = dk.kutu_hali(True, True, True, 293, kam.VARSAYILAN_TAVAN)
            kaydet("K4 MUTANT M4b TAVAN-GERI -> 293 satir KUTU_ASILDI (KIRMIZI)",
                   hal == dk.KUTU_ASILDI, hal, dk.KUTU_ASILDI, notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 4c: OLUMSUZLAMA KOLU KOR EDILIR ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "kutu-arsivle.py",
                        "    return bool(ETIKET_OLUMSUZ_DESENI.search(_tr_normalize(baslik)))",
                        "    return False", "K4_OLUMSUZ_KOR")
        if not ok:
            kaydet("K4 MUTANT M4c OLUMSUZ-KOR", False, notu, "capa uygulanmali")
        else:
            kam = modul_yukle("k4_m4c", os.path.join(ht, "kutu-arsivle.py"))
            b2, _g2, _d2, o2 = kam.korumali_etiketli_bloklar(satirlar, baslar)
            kaydet("K4 MUTANT M4c OLUMSUZ-KOR -> veto 1->3, ETIKET_OLUMSUZ=0 (KIRMIZI)",
                   len(b2) == 3 and len(o2) == 0,
                   "veto=%d olumsuz=%d" % (len(b2), len(o2)), "veto=3 olumsuz=0", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
def main():
    print("=" * 100)
    print("TIKAYICI KALDIRMA KABUL BATARYASI — 11 Eyl 2026 Okan emri, dilim 2")
    print("KOK = " + KOK)
    print("=" * 100)
    kalem1_kos()
    kalem2_kos()
    kalem3_kos()
    kalem4_kos()

    gecen = sum(1 for s in sonuclar if s[1])
    print()
    for ad, gecti, olculen, beklenen, notu in sonuclar:
        print("%s  %-62s olculen=%-28s beklenen=%s%s"
              % ("✅" if gecti else "❌", ad, olculen, beklenen,
                 ("  [" + notu + "]") if notu else ""))
    print("=" * 100)
    print("VAKA %d/%d GECTI" % (gecen, len(sonuclar)))
    if gecen != len(sonuclar):
        print("SONUC: KIRMIZI")
        return 1
    print("SONUC: YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
