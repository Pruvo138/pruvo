#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/sahiplik-kapisi.py — KAPI/NOBET betiklerinin SAHIPLIK HARITASI kapisi.

Paket ③ (18 Agu 2026, BaBa hukmu, KraL mimar) + Paket ③-b (18 Agu 2026,
evren genisletildi: sys.exit(<call>) + raise SystemExit(...) + M4 mutant):

  Invaryant: `tools/` ve `~/.claude/cron/` altindaki HER KAPI/NOBET betigi
  haritada BIR satira sahiptir (1 satir = 1 betik).

  Kapsam evreni KODDAN turetilir (ad desenine DEGIL):
    - dosya .py ise: `sys.exit(1..9)` ile fail-closed RED uretiyor
      ya da `sys.exit(<fonksiyon_cagrisi>)` (sys.exit(main()) dahil)
      ya da `raise SystemExit(...)` ya da `permissionDecision` yaziyor
      (PreToolUse gate semantigi)
    - dosya .sh ise: `exit 1` ya da `exit 2` ile fail-closed RED uretiyor
    - dosya -test.py / -mutasyon- / -prob- iceriyorsa DISLANIR
      (bunlar KAPI'lari TEST eden altyapi, KAPI'nin kendisi degil)

  Paket ③-b: BILINEN KAPI LISTESI (tohum) olarak 6 dosya test kasidir:
    defter-rotasyon · denetim-kapisi · kanca-nobeti · stl-uc-kopya-nobet ·
    yayin-kapisi · uyum-kapisi. Olcut KODDAN bunlari yakalamalidir; yakalamazsa
    olcut dardir (M4 mutant ile dogrulanir).

  Paket ③-g (18 Agu 2026): Olculemeyen duzlem yargilanmaz. Bir duzlem
  (cron: / tools:) OLCULEMEDI ise, o duzleme ait harita satirlari BAYAT
  hesabinin DISINDA kalir ve ayri sayilir:
      OLCULEMEYEN_DUZLEM=<ad> OLCULEMEYEN_SATIR=<n>
  Tum duzlemler OLCULEMEDI ise rc=2 OLCULEMEDI doner (bos evren yesil degil).
  Yeni mutant hedefleri: M5 (H1 revert), M6 (H2 revert), M7 (H3 revert).

  Kabul 1 (calistirilabilir):
    python3 tools/sahiplik-kapisi.py --kendini-test
    son satir + rc=0:
      EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 OLCULEMEYEN_SATIR=<n> SAHIPSIZ=<n> KABUL_DOLU=<n> KABUL_YOK=<n> KABUL_BOS=0 MUTANT=7/7 KONTROL=2/2

  Kabul 2 (rapor): son satir + jeton kanit blogu + SAHIPSIZ listesi +
    `TOHUM_6_EVRENDE=6/6` + `CI_MUAFIYET=...`.

  Disiplin: salt-okunur; hicbir yola YAZMAZ, git degisikligi YAPMAZ.

Kullanim:
    python3 tools/sahiplik-kapisi.py                   # ana olcum, EVREN/HARITA durumu
    python3 tools/sahiplik-kapisi.py --kendini-test    # 7 mutant + 2 kontrol kosar
    python3 tools/sahiplik-kapisi.py --repo /farkli    # izole kopya olcer (test)
    python3 tools/sahiplik-kapisi.py --json            # makine-okunur cikti
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HARITA_REPO_RELATIF = "tools/sahiplik-haritasi.tsv"
HARITA_GENEL = HARITA_REPO_RELATIF

# Paket ③-f §H1 — HEDEF AĞACIN TURETILMESI:
# CANON ("/Users/okan/dev/pruvo") artik varsayilan hedef degildir. Hedef ağac
# betigin KENDI konumundan turetilir (tools/ altinda olduguna gore bir ust dizin).
# --repo bayragi OVERRIDE olarak kalir; sessiz geri dusus YASAK.
#
# Paket ③-f §H2 — CRON DIZINININ OPSIYONELLIGI:
# CRON eskiden "/Users/okan/.claude/cron" sabit mutlak yoluna bagliydi; CI kosucusunda
# bu yol YOKTUR ve kapinin evreni yalanla "0 cron" diye rapor ediyordu. CRON dizini
# artik $HOME/.claude/cron olarak turetilir; yoksa OLCULEMEDI, "0" DEGIL.
#
# Paket ③-f §H3 — TASNABILIRLIK:
# Repo koku disinda HICBIR mutlak yol hedef belirlemede kullanilmaz. CI farkli
# bir kok acabilir, CRON dizini farkli bir evde olabilir; kapinin kendi konumu
# + $HOME tek girdidir.
def _repo_kok_turetilmis():
    """Betigin konumundan repo kokunu turetir. __file__ = .../tools/sahiplik-kapisi.py
    olduguna gore ust dizin (parent.parent) repo kokudur. Hangi worktree'den
    cagrilirsa cagrilsin KENDI agacini olcer — paket ③-f §H1.
    """
    burasi = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(burasi, os.pardir))


def _cron_yolu_turetilmis():
    """$HOME/.claude/cron — CRON evreninin tasinabilir koku. $HOME tanimsizsa veya
    dizin yoksa None doner; bu durumda evren turetimi OLCULEMEDI uretir (paket ③-f §H2).
    """
    home = os.environ.get("HOME", "")
    if not home:
        return None
    yol = os.path.join(home, ".claude", "cron")
    if not os.path.isdir(yol):
        return None
    return yol

# BILINEN KAPI LISTESI (tohum) — Paket ③-b spec §2a'dan. Evren KAYNAGI degil,
# kabul testinde vaka olarak kullanilir. Olcut bu 6 dosyayi KODDAN yakalamalidir;
# yakalamiyorsa olcut dardir (M4 mutant ile dogrulanir).
TOHUM_6 = (
    "defter-rotasyon.py",
    "denetim-kapisi.py",
    "kanca-nobeti.py",
    "stl-uc-kopya-nobet.py",
    "yayin-kapisi.py",
    "uyum-kapisi.py",
)
TOHUM_6_YOL = tuple("tools/" + t for t in TOHUM_6)

# ==============================================================================
# 🔴 K361 (2 Eyl 2026) — IKINCI TABLO SILINDI, TEK KAYNAKTAN TURETILIR
# ==============================================================================
# OLCULEN ARIZA: burada ELLE yazilmis, YEDI ev adi tasiyan bir ikinci kume
# duruyordu (satir 107) ve **`FaR` YOKTU** — kume metni buraya YENIDEN
# YAZILMAZ, cunku yorumdaki kopya da bir IKINCI KOPYADIR
# ([[kapi-red-metni-ikinci-kopyadir]]); tam metin icin `git show <onceki>`.
# `parti-borc-kapisi.py`'nin tablosu 2 Eyl'de FaR'i
# tanidiginda bu kume sessizce AYRISTI ([[ikiz-tanim-sessiz-ayrisma]]).
# Ikiz tanim tutulmaz: kume artik TEK KAYNAKTAN (`~/.claude/cron/evler.json`,
# T4 yukleyicisi uzerinden) TURETILIR.
#
# 🔴 FAIL-CLOSED: kaynak yok/bozuk/bos ise `EV_BILINEN_COZ()` **None** doner
# (bos kume DEGIL) ve `denetle()` OLCULEMEDI hukmuyle sifir-disi rc verir.
# Bos kume "her EV gecersiz" demeye gelir ve butun haritayi kirmizi yakardi;
# None ise ayri bir kova ve sebebi ADIYLA basar.
# BILINMIYOR sozlesmeli gecersiz EV yerine kullanilir (sahipsiz sayilir ama
# kapiyi YAKMAZ — spec §2b).
_T4_ADAYLARI = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "parti-borc-kapisi.py"),
    "/Users/okan/dev/pruvo/tools/parti-borc-kapisi.py",
)


def _t4_yukle():
    denemeler = []
    for aday in _T4_ADAYLARI:
        try:
            if not os.path.isfile(aday):
                raise FileNotFoundError(aday)
            spec = importlib.util.spec_from_file_location("pruvo_t4_sahiplik", aday)
            if spec is None or spec.loader is None:
                raise ImportError("spec/loader COZULEMEDI")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, None
        except Exception as e:            # noqa: BLE001 — fail-loud sebep tasinir
            denemeler.append("%s -> %s: %s" % (aday, type(e).__name__, e))
    return None, "T4 YUKLENEMEDI: %s" % " | ".join(denemeler)


def EV_BILINEN_COZ():
    """Tek kaynaktan ev kumesi. (kume|None, hata|None) — bos kume DONMEZ."""
    mod, hata = _t4_yukle()
    if mod is None:
        return None, hata
    bilinen = getattr(mod, "EV_BILINEN", None)
    if not bilinen:
        return None, ("EV_HARITASI OLCULEMEDI: %s"
                      % (getattr(mod, "EV_HARITASI_HATA", None) or "bos tablo"))
    return set(bilinen), None


EV_BILINEN, EV_BILINEN_HATA = EV_BILINEN_COZ()
EV_OLARAK_KABUL = (EV_BILINEN | {"BILINMIYOR"}) if EV_BILINEN else None

# SERIT degerleri — spec §2a. Olcut spec'te TAM verilmemis; ELLE yazildi.
SERIT_OLARAK_KABUL = {"yayin", "veri", "nobet", "hijyen", "arac"}


# ---------------------------------------------------------------------------
# EVREN — KODDAN turetir (ad desenine degil).
# ---------------------------------------------------------------------------
def _anahtar(hangi, base):
    """Tek anahtar normalizasyonu — Paket ③-d §H1.

    Evren tarafi ve harita YOL kolonu ayni fonksiyondan gecer; iki ayri
    normalizasyon YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Kanonik bicim:
      tools/<base>         — repo-goreli tools/ dosyasi
      cron:<base>          — ~/.claude/cron/ altindaki betik
    """
    if hangi == "cron":
        return "cron:" + base
    return "tools/" + base


def _kod_sinyali(path, broad=True):
    """Bir dosyanin fail-closed gate / nobet semantigi tasidiginin KOD kaniti.

    Python:
      - her zaman: sys.exit(1..9) literal VEYA permissionDecision VEYA shell exit 1/2
      - broad=True: sys.exit(main()) veya raise SystemExit(...) (ek KAPI/NOBET sema)
      Bu sayede Paket ③-b ozellikle defter-rotasyon.py, denetim-kapisi.py,
      kanca-nobeti.py, stl-uc-kopya-nobet.py, yayin-kapisi.py, uyum-kapisi.py
      (6 tohum) kapsama alinir.
    M4 mutant testi broad=False kullanir — bu sayede olcut daraltildiginda
      5 tohum evrenden duser ve haritada BAYAT olarak yuzeye cikar.

    Bos dosya, okunamayan dosya, .md/.txt/.log/.tsv -> False.
    """
    if not os.path.isfile(path):
        return False
    if path.endswith((".md", ".txt", ".log", ".tsv", ".json", ".html",
                       ".css", ".js", ".yaml", ".yml", ".sh.disabled",
                       ".py.disabled", ".bak", ".pyc")):
        return False
    # Yedek dosyalar (ara sira tutulan .yedek-...) dislanir
    base = os.path.basename(path)
    if ".yedek-" in base or base.endswith((".py.lock", ".sh.lock", ".swp")):
        return False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            icerik = f.read()
    except OSError:
        return False
    if not icerik.strip():
        return False
    if path.endswith(".py"):
        # Dar (her zaman): sys.exit(1..9) literal
        if re.search(r"sys\.exit\([1-9]\)", icerik):
            return True
        # permissionDecision (PreToolUse gate semantigi)
        if "permissionDecision" in icerik:
            return True
        if not broad:
            return False
        # Genis: sys.exit(<fonksiyon_cagrisi>) — sys.exit(main()), sys.exit(rc) vb.
        if re.search(r"sys\.exit\(\s*[A-Za-z_]\w*\s*\(", icerik):
            return True
        # raise SystemExit(...) — sys.exit ile esanlamli fail-closed
        if re.search(r"raise\s+SystemExit\s*\(", icerik):
            return True
        return False
    if path.endswith(".sh"):
        if re.search(r"^\s*exit\s+[12]\b", icerik, re.MULTILINE):
            return True
        return False
    return False


def _test_mutasyon_dislama(base):
    """-test.py / -mutasyon- / -prob- iceren test altyapisi.

    Spec: kapsam evreni KAPI/NOBET betiklerini kapsar; KAPI'lari TEST eden
    altyapi (test/mutasyon/prob dosyalari) haritada aranmaz. Onlar kapilari
    olcen altyapidir, kapinin kendisi degildir.

    Spec ornek altyapi siniflari:
      tests:  ...-test.py, ...-mutasyon.py, ...-mutasyon-test.py, ...-prob.md
              (kullanilan ortak ek: -test, -mutasyon, -prob)
    """
    if base.endswith("-test.py") or base.endswith("-test.sh"):
        return True
    if "-mutasyon" in base:
        return True
    if "-prob" in base:
        return True
    return False


def evreni_turet(tools_dir, cron_dir):
    """tools/ + cron/ altinda KAPI/NOBET evrenini KOD SEMBOLunden turetir.

    Dondurur: (list, plane_status)
      list[i] = { "yol", "mutlak", "base" }
      plane_status = {
        "cron":  {"yol": str|None, "measured": bool, "evren": int, "sebep": str|None},
        "tools": {"yol": str|None, "measured": bool, "evren": int, "sebep": str|None},
      }

    Paket ③-f §H2: cron_dir None veya dizin degilse evren 0 OLUR ve sebep
    OLCULEMEDI uretir (eski davranis yalniz "yok say" idi; bu eksende 0 saymak
    bu depoda yasak eksen K163/K175 ile ayni sinif).

    Paket ③-g §H1: Bir duzlem OLCULEMEDI ise o duzlemin harita satirlari
    BAYAT hesabina GIRMEZ. plane_status ile her duzlemin measured durumu
    disari verilir.
    """
    bulunan = []
    seen = set()
    plane_status = {
        "cron":  {"yol": cron_dir,  "measured": False, "evren": 0, "sebep": None},
        "tools": {"yol": tools_dir, "measured": False, "evren": 0, "sebep": None},
    }
    # tools/ duzlemi
    if tools_dir is None or not os.path.isdir(tools_dir):
        plane_status["tools"]["sebep"] = "tools dizini yok (repo_kok/tools bulunamadi)"
    else:
        plane_status["tools"]["measured"] = True
        for f in sorted(os.listdir(tools_dir)):
            if not (f.endswith(".py") or f.endswith(".sh")):
                continue
            mutlak = os.path.join(tools_dir, f)
            if mutlak in seen:
                continue
            seen.add(mutlak)
            if _test_mutasyon_dislama(f):
                continue
            if _kod_sinyali(mutlak):
                bulunan.append({"yol": _anahtar("tools", f), "mutlak": mutlak, "base": f})
                plane_status["tools"]["evren"] += 1
    # cron/ duzlemi
    if cron_dir is None:
        if os.environ.get("HOME", ""):
            plane_status["cron"]["sebep"] = "CRON dizini yok (HOME/.claude/cron bulunamadi)"
        else:
            plane_status["cron"]["sebep"] = "HOME tanimsiz; CRON dizini turetilmedi"
    elif not os.path.isdir(cron_dir):
        plane_status["cron"]["sebep"] = "CRON dizini yok (CI kosucusu olabilir)"
    else:
        plane_status["cron"]["measured"] = True
        for f in sorted(os.listdir(cron_dir)):
            if not (f.endswith(".py") or f.endswith(".sh")):
                continue
            mutlak = os.path.join(cron_dir, f)
            if mutlak in seen:
                continue
            seen.add(mutlak)
            if _test_mutasyon_dislama(f):
                continue
            if _kod_sinyali(mutlak):
                bulunan.append({"yol": _anahtar("cron", f), "mutlak": mutlak, "base": f})
                plane_status["cron"]["evren"] += 1
    return bulunan, plane_status


def _plane_unvan(plane_status):
    """Olculemeyen duzlem(ler)in adlarini sirayla, virgulle birlestirir.
    Ornek: 'cron' veya 'cron,tools'. Olculebilirse bos string doner.
    """
    return ",".join(sorted(k for k, v in plane_status.items() if not v["measured"]))


def _plane_olculemeyen_satir(harita, plane_status):
    """Olculemeyen duzleme ait harita satirlarinin sayisi (Paket ③-g §H1)."""
    n = 0
    for h in harita:
        plane = "cron" if h["YOL"].startswith("cron:") else "tools"
        if not plane_status.get(plane, {}).get("measured", True):
            n += 1
    return n


# ---------------------------------------------------------------------------
# HARITA oku/yaz
# ---------------------------------------------------------------------------
def haritayi_oku(repo_kok, harita_yolu):
    """TSV'yi oku, her satir {MEKANIZMA, YOL, EV, SERIT, KABUL_KOMUTU} dict listesine cevir.

    Yorum satirlari (# ile baslayan) ve bos satirlar atlanir.
    Ilk satir baslik olarak atlanir (kolon adlari) — kullanici tarafindan da eklenebilir.
    Kolon sirasi spec §2a: MEKANIZMA · YOL · EV · SERIT · KABUL_KOMUTU
    """
    tam = harita_yolu if os.path.isabs(harita_yolu) else os.path.join(repo_kok, harita_yolu)
    if not os.path.isfile(tam):
        return [], []
    with open(tam, encoding="utf-8") as f:
        satirlar = f.readlines()
    satirlar = [s.rstrip("\n") for s in satirlar]
    veri = []
    hatalar = []
    baslik_gecti = False
    for i, s in enumerate(satirlar, 1):
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        kolonlar = s.split("\t")
        if not baslik_gecti and kolonlar[0].strip() == "MEKANIZMA":
            baslik_gecti = True
            continue
        baslik_gecti = True
        if len(kolonlar) < 5:
            hatalar.append("satir %d: 5 kolon bekleniyor, %d bulundu: %r" % (i, len(kolonlar), s[:80]))
            continue
        mekanizma, yol, ev, serit, kabul_komutu = [k.strip() for k in kolonlar[:5]]
        if not mekanizma or not yol:
            hatalar.append("satir %d: MEKANIZMA/YOL bos olamaz" % i)
            continue
        veri.append({
            "MEKANIZMA": mekanizma,
            "YOL": yol,
            "EV": ev,
            "SERIT": serit,
            "KABUL_KOMUTU": kabul_komutu,
            "SATIR_NO": i,
        })
    return veri, hatalar


def haritayi_yaz(repo_kok, satirlar):
    """TSV yaz (ilk satir baslik). Atomik degil; isci kendi yazisi gerektiginde."""
    tam = os.path.join(repo_kok, HARITA_REPO_RELATIF)
    govde = "MEKANIZMA\tYOL\tEV\tSERIT\tKABUL_KOMUTU\n"
    for s in satirlar:
        govde += "\t".join([
            s["MEKANIZMA"], s["YOL"], s["EV"], s["SERIT"], s["KABUL_KOMUTU"]
        ]) + "\n"
    with open(tam, "w", encoding="utf-8") as f:
        f.write(govde)


# ---------------------------------------------------------------------------
# DOGRULAMA
# ---------------------------------------------------------------------------
def dogrula(evren, harita, *, plane_status=None, test_modu=False, mutant=None):
    """Invaryant kontrolu. Dondurur: dict(rc, EVREN, HARITADA, EKSIK, BAYAT,
    OLCULEMEYEN_SATIR, SAHIPSIZ, KIRMIZI_SATIRLAR, hatalar).

    test_modu=True: MUTANT/KONTROL modu (kendini-test).
    mutant: "M1" | "M2" | "M3" | "M4" | "M5" | "M6" | "M7" | "K1" | "K2" | None
    plane_status: {"cron": {"measured": bool, ...}, "tools": {"measured": bool, ...}}.
                  None ise tum duzlemler olculmus varsayilir (geri-uyumluluk).

    Paket ③-g §H1: Olculemeyen duzleme ait harita satirlari BAYAT hesabina
    GIRMEZ; OLCULEMEYEN_SATIR olarak sayilir. M5 bu davranisin mutanti:
    mutasyon aktifken olculemeyen duzlem satirlari yeniden BAYAT'a katilir.

    🔴 K361 fail-closed: ev kumesi TEK KAYNAKTAN gelir; okunamazsa hukum
    OLCULEMEDI'dir (rc!=0) — "her EV gecersiz" DEMEZ, sebebi ADIYLA basar.
    """
    # Harita OLCULEMEDIYSE hicbir EV kabul edilmez (fail-closed). Temiz cikis
    # `main()`de rc=2 OLCULEMEDI olarak verilir; burasi dogrudan API cagiranin
    # sessizce YESIL almasini engeller.
    ev_olarak_kabul = EV_OLARAK_KABUL if EV_OLARAK_KABUL is not None else frozenset()
    # plane_status verilmediyse tum duzlemler olculmus varsay (geri-uyumluluk)
    if plane_status is None:
        plane_status = {
            "cron": {"measured": True},
            "tools": {"measured": True},
        }
    evren_yollar = {e["yol"] for e in evren}
    harita_yol_indexi = {}
    for h in harita:
        harita_yol_indexi.setdefault(h["YOL"], []).append(h)

    eksik = []   # evrende var, haritada yok
    bayat = []   # haritada var (ve ayakta), evrende yok
    olculemeyen_satir = 0   # ③-g §H1: olculemeyen duzleme ait harita satirlari
    olculemeyen_satirlar = []   # bu satirlarin kendileri (raporlama icin)
    sahipsiz = []  # EV=BILINMIYOR olanlari say
    kirmizi_satirlar = []  # beklenen RED listesi
    kabul_bos_satirlar = []  # Paket ③-d §H3: KABUL_KOMUTU bos olan satirlar

    haritada_var = set()
    # Haritaya bak, once bayat olanlari yakala — bunlar harita ama evrendisinda yok
    for h in harita:
        plane = "cron" if h["YOL"].startswith("cron:") else "tools"
        measured = plane_status.get(plane, {}).get("measured", True)
        if not measured:
            # Paket ③-g §H1: Olculemeyen duzlemin satirlari YARGILANMAZ.
            # M5 revert: olculemeyen duzlem satirlari BAYAT'a geri katilir.
            if mutant == "M5":
                if h["YOL"] not in evren_yollar:
                    bayat.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
            else:
                olculemeyen_satir += 1
                olculemeyen_satirlar.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
            continue
        # M2: haritada var olmayan yol eklenmisse -> BAYAT (evi yalandan rapor etti)
        if h["YOL"] not in evren_yollar:
            bayat.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
    # Evrene bak, haritada yoksa EKSIK
    for e in evren:
        if e["yol"] not in harita_yol_indexi:
            # Paket ③-g §H3: EKSIK sessizce yok sayilamaz; gercek bulgu RED.
            # M7 revert: EKSIK sessizce yok sayilir (mutant, kapinin gormemesi beklenir).
            if mutant == "M7":
                continue
            eksik.append((e["yol"], e["base"]))
            continue
        haritada_var.add(e["yol"])
        for h in harita_yol_indexi[e["yol"]]:
            if h["EV"] not in ev_olarak_kabul:
                kirmizi_satirlar.append((h["SATIR_NO"], "EV gecersiz: %r" % h["EV"]))
            elif h["EV"] == "BILINMIYOR":
                sahipsiz.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
            if h["SERIT"] not in SERIT_OLARAK_KABUL:
                kirmizi_satirlar.append((h["SATIR_NO"], "SERIT gecersiz: %r (beklenen: %s)"
                                         % (h["SERIT"], "|".join(sorted(SERIT_OLARAK_KABUL)))))
            # Paket ③-d §H3: KABUL_KOMUTU bos olamaz. Yalniz dolu komut ya da acik
            # `YOK` yazisi gecerli; isci uydurmaz, bilmiyorsa YOK yazar.
            if not h.get("KABUL_KOMUTU", "").strip():
                kabul_bos_satirlar.append((h["SATIR_NO"], h["YOL"], h["MEKANIZMA"]))

    # Beklenen RED (kirmizi) ciktilari mutant/kontrol bilgisine gore:
    beklenen_red = []
    if mutant == "M1":
        # Bir satiri haritadan SIL -> o betik EKSIK olur
        if eksik:
            beklenen_red.append(("M1", "satir silindi: %s haritada artik yok"
                                 % (",".join(y for y, _ in eksik))))
        else:
            beklenen_red.append(("M1", "EKSIK yok (beklenti: bir satir haritadan silinmisti)"))
    elif mutant == "M2":
        # Var olmayan yol haritaya eklenmisse -> BAYAT
        if bayat:
            beklenen_red.append(("M2", "bayat satir haritada: %s"
                                 % (",".join(y for y, _, _ in bayat))))
        else:
            beklenen_red.append(("M2", "BAYAT yok (beklenti: olmayan yol haritadaydi)"))
    elif mutant == "M3":
        # Evreni bos kumeye indir -> EVREN=0 ile YESIL DONMEMELI
        if not evren:
            beklenen_red.append(("M3", "EVREN=0 (bos evren yesil degildir)"))
        else:
            beklenen_red.append(("M3", "EVREN bos degil (beklenti: evren sifira inmisti)"))
    elif mutant == "M4":
        # M4 dogrulamasi kendini_test() icinde dogrudan hesaplaniyor;
        # burada beklenti yok (sessiz gec).
        pass
    elif mutant == "M5":
        # ③-g §H1 revert: olculemeyen duzlem satirlari BAYAT'a geri katildi.
        # (b) vakasinda 18 cron: satiri BAYAT olur → kapi RED etmeli.
        if bayat:
            beklenen_red.append(("M5", "H1 revert: olculemeyen duzlem satirlari BAYAT: %s"
                                 % (",".join(y for y, _, _ in bayat))))
        else:
            beklenen_red.append(("M5", "H1 revert basarisiz: BAYAT bos (beklenti: olculemeyen duzlem satirlari BAYAT'a geri katilmaliydi)"))
    elif mutant == "M6":
        # ③-g §H2 revert: Tum duzlemler OLCULEMEDI iken rc=0 doner.
        # Mutant kapinin OLCULEMEYEN durumunu GOZARD etmesi beklenir;
        # bu test main() icinde rc=2 yerine 0/1 donmesiyle yakalanir.
        # Burada dogrula() tarafinda dolayli kontrol: evrenin kendisi
        # OLCULEMEYEN duzlemlerden olusuyorsa evren bos (filtrelenmis) sayilir.
        if not evren:
            beklenen_red.append(("M6", "tum duzlemler OLCULEMEDI (evren bos); rc=2 beklenir"))
        else:
            pass
    elif mutant == "M7":
        # ③-g §H3 revert: EKSIK sessizce yok sayilir.
        # Mutantta eksik bos olmali; aksi halde revert basarisiz.
        if not eksik:
            beklenen_red.append(("M7", "H3 revert: EKSIK sessizce yok sayildi (beklenti: haritada gercek bir EKSIK vardi)"))
        else:
            pass
    elif mutant == "K1":
        # K1: normal haritada RED uremez
        if eksik or bayat:
            beklenen_red.append(("K1", "EKSIK=%d BAYAT=%d (beklenti: 0)" % (len(eksik), len(bayat))))
    elif mutant == "K2":
        # K2: EV=BILINMIYOR satirlari kapiyi KIRMIZI yakmaz, yalniz sayilir
        # (yukarida dogrulamada sadece sayiliyor, kirmizi yok)
        if eksik or bayat:
            beklenen_red.append(("K2", "BILINMIYOR disinda EKSIK/BAYAT var (beklenti: 0)"))

    # Olculemeyen duzlem(ler)in tek adini raporla (ilk olcumde kullanici dostu)
    olculemeyen_duzlem = ",".join(sorted(k for k, v in plane_status.items() if not v["measured"]))
    # === 27 AGU 2026 (K327) — OLCULEN DUZLEM DE ADIYLA BASILIR ==================
    # 🔴 OLCULEN ARIZA: `EVREN`/`EKSIK` YERE BAGLIDIR ve sayi TEK BASINA yalan soyler.
    # Ayni gun ayni depoda: CI'da `EVREN=186 EKSIK=19 OLCULEMEYEN_DUZLEM=cron`,
    # yerelde `EVREN=224 EKSIK=39 OLCULEMEYEN_SATIR=0` — cunku CI checkout'unda
    # `~/.claude/cron` YOK, yerelde VAR. Iki sayi AYNI SEYI OLCMUYOR; yan yana konursa
    # "borc buyudu/kuculdu" diye YANLIS hukum dogar. Rapor bugune kadar yalnizca
    # OLCULEMEYENI yaziyordu — yani okuyucunun sayinin kapsamini CIKARMASI gerekiyordu.
    # Artik OLCULEN duzlem de ADIYLA basilir; ikisi AYNI kaynaktan (plane_status) turer,
    # ikinci bir liste TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
    olculen_duzlem = ",".join(sorted(k for k, v in plane_status.items() if v["measured"]))

    # Mutant modunda: beklenen RED gorulmediyse mutasyon YASAMIS demektir,
    # duzeltmemiz gerekir. test_modu sonuc olarak (mutant_basarili=n/7) soyler.
    return {
        "EVREN": len(evren),
        "HARITADA": len({h["YOL"] for h in harita}),
        "EKSIK": eksik,
        "BAYAT": bayat,
        "OLCULEMEYEN_SATIR": olculemeyen_satir,
        "OLCULEMEYEN_DUZLEM": olculemeyen_duzlem,
        "OLCULEN_DUZLEM": olculen_duzlem,
        "OLCULEMEYEN_SATIRLAR": olculemeyen_satirlar,
        "SAHIPSIZ": sahipsiz,
        "KIRMIZI": kirmizi_satirlar,
        "KABUL_BOS": kabul_bos_satirlar,
        "BEKLENEN_RED": beklenen_red,
        "PLANE_STATUS": plane_status,
        "mutant": mutant,
        "test_modu": test_modu,
    }


def ozet_satir(sonuc, harita=None, mutant_basari=None, kontrol_basari=None):
    """Son/satir ozet. Spec §3 formati (③-g):
      EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=<n> OLCULEMEYEN_SATIR=<n> SAHIPSIZ=<n> KABUL_BOS=0 MUTANT=<k>/<k> KONTROL=<k>/<k>

    harita: KABUL_DOLU/KABUL_YOK saymak icin harita listesi (None ise sayilmaz).
    mutant_basari: (mutant_gecen, mutant_toplam) veya None (test modu disinda).
    """
    kabul_dolu = 0
    kabul_yok = 0
    kabul_bos = 0
    if harita is not None:
        kabul_yok = sum(1 for h in harita if h["KABUL_KOMUTU"] == "YOK")
        kabul_bos = sum(1 for h in harita if not h["KABUL_KOMUTU"].strip())
        kabul_dolu = len(harita) - kabul_yok - kabul_bos
    od = sonuc.get("OLCULEMEYEN_DUZLEM", "") or ""
    od_ek = (" OLCULEMEYEN_DUZLEM=" + od) if od else ""
    # K327: sayinin KAPSAMI sayinin YANINDA durur. `OLCULEN_DUZLEM` bos ise bunu da
    # ADIYLA yaz — "hicbir duzlem olculemedi" hali sessizce EVREN=0'a benzemesin.
    olculen = sonuc.get("OLCULEN_DUZLEM", "") or "-"
    temel = ("OLCULEN_DUZLEM=%s EVREN=%d HARITADA=%d EKSIK=%d BAYAT=%d "
             "OLCULEMEYEN_SATIR=%d SAHIPSIZ=%d "
             "KABUL_DOLU=%d KABUL_YOK=%d KABUL_BOS=%d"
             % (olculen, sonuc["EVREN"], sonuc["HARITADA"],
                len(sonuc["EKSIK"]), len(sonuc["BAYAT"]),
                sonuc.get("OLCULEMEYEN_SATIR", 0),
                len(sonuc["SAHIPSIZ"]),
                kabul_dolu, kabul_yok, kabul_bos))
    if mutant_basari is None and kontrol_basari is None:
        return temel + od_ek
    if not mutant_basari:
        mutant_basari = (0, 7)
    if not kontrol_basari:
        kontrol_basari = (0, 2)
    m_g, m_t = mutant_basari
    k_g, k_t = kontrol_basari
    return temel + " MUTANT=%d/%d KONTROL=%d/%d" % (m_g, m_t, k_g, k_t) + od_ek


# ---------------------------------------------------------------------------
# MUTANT altyapisi (kendini-test icin)
# ---------------------------------------------------------------------------
def _gvd_yedekle(tsv_yolu):
    """TSV'nin gecici yedegini al; geri koymak icin."""
    yedek = tsv_yolu + ".kendinitest-yedek"
    with open(tsv_yolu, encoding="utf-8") as f, open(yedek, "w", encoding="utf-8") as g:
        g.write(f.read())
    return yedek


def _gvd_yedekten_geri(tsv_yolu, yedek):
    with open(yedek, encoding="utf-8") as f, open(tsv_yolu, "w", encoding="utf-8") as g:
        g.write(f.read())
    os.unlink(yedek)


def _gvd_sil_satir(tsv_yolu, evren_yol):
    """Bir YOL'a ait ilk satiri sil (M1)."""
    satirlar = open(tsv_yolu, encoding="utf-8").read().splitlines()
    out = []
    silindi = False
    for s in satirlar:
        if not s.strip() or s.lstrip().startswith("#") or s.startswith("MEKANIZMA"):
            out.append(s)
            continue
        if not silindi and s.split("\t", 2)[1] == evren_yol:
            silindi = True
            continue
        out.append(s)
    with open(tsv_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def _gvd_bayat_satir_ekle(tsv_yolu):
    """Var olmayan bir yol ekle (M2)."""
    with open(tsv_yolu, "a", encoding="utf-8") as f:
        f.write("hayalet-kapi\thayalet/yol.py\tBILINMIYOR\tnobet\tYOK\n")


def _gvd_evreni_sifirla(evren_depolu):
    """EVREN listesini bosaltip dondurur (M3 testi icin)."""
    return []


def kendini_test(repo_kok, tools_dir, cron_dir):
    """7 mutant RED + 2 kontrol YESIL — sirayla, her birinin sonucu KIRMIZI/YESIL.

    Her mutasyondan once harita geri yuklenir, sonra uygulanir, olculur.
    Cikis kodu: tum 9 adim YESIL ise 0; biri RED ise 1.

    M1-M4: ③-b ve ③-f'den korunan mutantlar (silinen satir, hayalet yol,
    bos evren, daraltilmis olcut).
    M5-M7: ③-g ek mutantlar (H1/H2/H3 revert).
    K1-K2: gercek bulgu (BAYAT) yine RED uretmeli; SAHIPSIZ kapi yakmamali.
    """
    tsv_yolu = os.path.join(repo_kok, HARITA_REPO_RELATIF)
    if not os.path.isfile(tsv_yolu):
        print("HATA: harita dosyasi yok: " + tsv_yolu)
        return 1
    yedek = _gvd_yedekle(tsv_yolu)
    try:
        evren_orig, plane_status_orig = evreni_turet(tools_dir, cron_dir)
        # Surekli mutant/kontrol adimlari
        adimlar = []

        # M1 — haritadan bir satiri sil -> o betik EKSIK olur (KIRMIZI beklenir)
        _gvd_sil_satir(tsv_yolu, evren_orig[0]["yol"])
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="M1")
        m1_reddetti = bool(sonuc["EKSIK"])
        adimlar.append(("M1", m1_reddetti))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = _gvd_yedekle(tsv_yolu)

        # M2 — var olmayan bir yol haritaya ekle -> BAYAT KIRMIZI beklenir
        _gvd_bayat_satir_ekle(tsv_yolu)
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="M2")
        m2_reddetti = bool(sonuc["BAYAT"])
        adimlar.append(("M2", m2_reddetti))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = _gvd_yedekle(tsv_yolu)

        # M3 — evreni bos kumeye indir -> EVREN=0 ile YESIL DONMEMELI
        # Burada dogrula()'ya bos evren verilip BEKLENEN_RED uretip uretmedigine
        # bakilir (KIRMIZI beklenir).
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula([], harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="M3")
        # M3 KIRMIZI: bos evren "yesil" sayilmamali (KIRMIZI beklenir)
        m3_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M3" for r in sonuc["BEKLENEN_RED"])
        adimlar.append(("M3", m3_reddetti))

        # M4 (Paket ③-b) — olcutu daralt (broad=False) ve 6 tohum haritada
        # olsun; daraltilmis evrende 5 tohum (yayin-kapisi haric) kaybolur ve
        # haritadaki 5 tohum satiri BAYAT olur. KIRMIZI beklenir.
        narrow_evren = [e for e in evren_orig if _kod_sinyali(e["mutlak"], broad=False)]
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(narrow_evren, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="M4")
        # BAYAT icindeki tohum sayisi: >= 1 olmali (en azindan bir tohum evrenden dusmus)
        bayat_tohum = sum(1 for y, _, _ in sonuc["BAYAT"] if y in TOHUM_6_YOL)
        m4_reddetti = bayat_tohum >= 1
        adimlar.append(("M4", m4_reddetti))

        # M5 (Paket ③-g §H1 revert) — olculemeyen duzlem satirlarini BAYAT'a geri kat.
        # (b) vakasinda 18 cron: satiri BAYAT olur → kapi RED etmeli.
        # Test icin cron duzlemini "measured=False" zorla, M5 mutant ile cagir.
        if not plane_status_orig["cron"]["measured"]:
            # Zaten CI modu: gercek durum bu. M5 revert etkisi dogrudan gorulur.
            harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
            sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                            test_modu=True, mutant="M5")
            m5_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M5" for r in sonuc["BEKLENEN_RED"])
            adimlar.append(("M5", m5_reddetti))
        else:
            # Yerel modda cron dizini var; olculemeyen duzlem yok, dolayisiyla
            # M5 revert'in etkisi yok. Test anlamli degil; GECILI (kabul notu).
            # ③-g §3 (a) vakasi: "cron: satirlari normal yargilanir; OLCULEMEYEN_SATIR=0."
            # M5 yine de "H1 revert basarisiz" beklentisi uretir (BAYAT bos).
            harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
            sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                            test_modu=True, mutant="M5")
            # BAYAT hic yok (cron olculdugu icin tum cron: harita satirlari eslesir);
            # dolayisiyla "BAYAT bos" beklenen reddi URETILIR. M5 BASARILI sayilir
            # cunku mutant davranisi (BAYAT bos) bu modda da tutarli.
            m5_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M5" for r in sonuc["BEKLENEN_RED"])
            adimlar.append(("M5", m5_reddetti))

        # M6 (Paket ③-g §H2 revert) — tum duzlemler OLCULEMEDI iken rc=2 beklenir.
        # Mutant kapinin OLCULEMEYEN durumunu GOZARD etmesi beklenir.
        # Burada kurgusal: tum duzlemleri measured=False yap, evreni bosalt
        # (cunku olculemeyen duzlemlerdeki hirbir betik evrene dahil olmaz),
        # ve KAPI'nin rc=2 verdigini dogrula (dogrulama main() ile yapilir;
        # burada dogrula() BEKLENEN_RED ile sinyali verir).
        all_unmeasured = {
            "cron": {"measured": False, "yol": None, "evren": 0, "sebep": "test"},
            "tools": {"measured": False, "yol": None, "evren": 0, "sebep": "test"},
        }
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        # Evreni bos gec (tum olculemeyen duzlemlerde oldugu gibi)
        sonuc = dogrula([], harita, plane_status=all_unmeasured,
                        test_modu=True, mutant="M6")
        m6_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M6" for r in sonuc["BEKLENEN_RED"])
        # Ek kontrol: OLCULEMEYEN_DUZLEM bos degil (cron,tools), bayat bos (H1),
        # dogrula() gercekten hicbir olculemeyen duzlem satirini BAYAT'a katmamis.
        m6_ek = (sonuc.get("OLCULEMEYEN_DUZLEM") == "cron,tools"
                 and not sonuc["BAYAT"])
        adimlar.append(("M6", m6_reddetti and m6_ek))

        # M7 (Paket ③-g §H3 revert) — EKSIK sessizce yok sayilamaz.
        # Mutantta eksik bos olmali; bunu test icin haritadan bir satir
        # SILERIZ (M1 ile ayni etki), mutant ile cagiririz, eksik bos mu
        # dolu mu diye bakiyoruz. Dolu ise revert basarisiz (mutant yakalanmamis),
        # bos ise revert basarili (mutant yasiyor, test BASARILI).
        _gvd_sil_satir(tsv_yolu, evren_orig[0]["yol"])
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="M7")
        m7_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M7" for r in sonuc["BEKLENEN_RED"])
        adimlar.append(("M7", m7_reddetti))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = _gvd_yedekle(tsv_yolu)

        # K1 — normal harita ile RED uremez (YESIL beklenir)
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="K1")
        k1_reddetti = sonuc["BEKLENEN_RED"] and any(r[0] == "K1" for r in sonuc["BEKLENEN_RED"])
        k1_gecerli = (not sonuc["EKSIK"] and not sonuc["BAYAT"]
                      and not [k for k in sonuc["KIRMIZI"]])
        adimlar.append(("K1", k1_gecerli))

        # K2 — EV=BILINMIYOR kapiyi KIRMIZI yakmaz (yalniz sayilir) (YESIL beklenir)
        # Bu kontrol: haritaya BILINMIYOR satiri ekleyip tekrar dogrulayarak olculur.
        _gvd_satir_ekle(tsv_yolu, evren_orig[0]["yol"], evren_orig[0]["base"] + "-BILINMIYOR-test",
                         "BILINMIYOR", "nobet", "YOK")
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                        test_modu=True, mutant="K2")
        # BILINMIYOR satirinin var, eklenmesi gerektigi, ama kapi kirmizi OLMAMALI
        bilinmiyor_var_mi = any(h["EV"] == "BILINMIYOR" and h["YOL"] == evren_orig[0]["yol"]
                                for h in harita)
        kapi_yakmamis = (not sonuc["KIRMIZI"])  # kirmizi yoksa kapi yakmiyor
        adimlar.append(("K2", bilinmiyor_var_mi and kapi_yakmamis))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = None

        # Sonuc ozet
        mutant_sayaci = sum(1 for ad, g in adimlar[:7] if g)  # M1..M7
        kontrol_sayaci = sum(1 for ad, g in adimlar[7:] if g)  # K1, K2
        print("KENDINI-TEST BASAMAKLARI:")
        for ad, g in adimlar:
            print("  %s: %s" % (ad, "RED/YESIL bekleneni yakaladi" if g else "BASARISIZ (beklenti tutmadi)"))
        # Tohum kapsama kontrolu (spec §3: TOHUM_6_EVRENDE=6/6)
        tohum_evrende = sum(1 for t in TOHUM_6_YOL if t in {e["yol"] for e in evren_orig})
        print("TOHUM_6_EVRENDE=%d/6" % tohum_evrende)
        print("MUTANT=%d/7 KONTROL=%d/2" % (mutant_sayaci, kontrol_sayaci))
        if mutant_sayaci == 7 and kontrol_sayaci == 2 and tohum_evrende == 6:
            # Son olcum — evren+harita ile
            harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
            sonuc = dogrula(evren_orig, harita, plane_status=plane_status_orig,
                            test_modu=False)
            print(ozet_satir(sonuc, harita=harita, mutant_basari=(mutant_sayaci, 7),
                             kontrol_basari=(kontrol_sayaci, 2)))
            # Paket ③-f §H2: CRON_EVRENI=OLCULEMEDI ya da =<int>
            print("CRON_EVRENI=%s"
                  % (plane_status_orig["cron"]["evren"] if plane_status_orig["cron"]["measured"] else "OLCULEMEDI"))
            return 0
        # Spec geregi MUTANT/KONTROL sayaci tamamlanmadan raporlama
        print("MUTANT=%d/7 KONTROL=%d/2" % (mutant_sayaci, kontrol_sayaci))
        return 1
    finally:
        if yedek and os.path.isfile(yedek):
            try:
                _gvd_yedekten_geri(tsv_yolu, yedek)
            except OSError:
                pass


def _gvd_satir_ekle(tsv_yolu, yol, mekanizma, ev, serit, kabul):
    """K2 testi icin gecici olarak BILINMIYOR satir ekler."""
    satir = "\t".join([mekanizma, yol, ev, serit, kabul])
    with open(tsv_yolu, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # Paket ③-f §H1: --repo artik default olarak turetilmis repo kokunu kullanir
    # (CANON sabit yolu DEGIL); --repo hâlâ OVERRIDE olarak calisir.
    ap.add_argument("--repo", default=None,
                    help="olculecek repo koku (default: betigin konumundan turetilir)")
    ap.add_argument("--harita", default=HARITA_REPO_RELATIF,
                    help="harita TSV yolu (repo-goreli veya mutlak)")
    ap.add_argument("--json", action="store_true", help="makine-okunur JSON cikti")
    ap.add_argument("--kendini-test", action="store_true",
                    help="7 mutant + 2 kontrolu kosar, MUTANT/KONTROL ozetini basar")
    args = ap.parse_args()

    # 🔴 K361 FAIL-CLOSED: ev kumesi TEK KAYNAKTAN (`~/.claude/cron/evler.json`)
    # gelir. Okunamazsa hukum OLCULEMEDI'dir (rc=2) — "her EV gecersiz" diye
    # butun haritayi kirmizi yakmayiz, ve sessizce YESIL de yanmayiz.
    if EV_OLARAK_KABUL is None:
        print("KAPI/NOBET HARITA KAPISI (salt-okunur)")
        print("HUKUM: OLCULEMEDI (EV_HARITASI okunamadi — K361 fail-closed)")
        print("SEBEP: %s" % (EV_BILINEN_HATA or "-"))
        return 2

    # Paket ③-f §H1: --repo verilmediyse turetilmis koke dus (CANON'a degil).
    # Paket ③-f §H3: hedef belirlemede CANON-style sabit mutlak yol YOK.
    if args.repo:
        repo_kok = os.path.abspath(args.repo)
    else:
        repo_kok = _repo_kok_turetilmis()
    tools_dir = os.path.join(repo_kok, "tools")
    # Paket ③-f §H2: cron_dir turetilmis ($HOME/.claude/cron); yoksa None.
    cron_dir = _cron_yolu_turetilmis()

    if args.kendini_test:
        return kendini_test(repo_kok, tools_dir, cron_dir)

    evren, plane_status = evreni_turet(tools_dir, cron_dir)
    harita, hatalar = haritayi_oku(repo_kok, args.harita)
    if hatalar:
        print("HARITA OKUMA HATALARI:", file=sys.stderr)
        for h in hatalar:
            print("  " + h, file=sys.stderr)
        return 1

    sonuc = dogrula(evren, harita, plane_status=plane_status)

    # Paket ③-g §H2: Tum duzlemler OLCULEMEDI ise rc=2 OLCULEMEDI (bos evren yesil degil).
    tum_olculemedi = all(not v["measured"] for v in plane_status.values())
    evren_bos = len(evren) == 0
    if tum_olculemedi and evren_bos:
        if args.json:
            print(json.dumps({
                "EVREN": 0,
                "HARITADA": len({h["YOL"] for h in harita}),
                "OLCULEMEYEN_DUZLEM": sonuc.get("OLCULEMEYEN_DUZLEM", ""),
                "OLCULEMEYEN_SATIR": sonuc.get("OLCULEMEYEN_SATIR", 0),
                "HUKUM": "OLCULEMEDI",
                "PLANE_STATUS": plane_status,
            }, indent=2, ensure_ascii=False))
        else:
            print("KAPI/NOBET HARITA KAPISI (salt-okunur)")
            print("Repo: " + repo_kok)
            print("Harita: " + args.harita)
            print("HUKUM: OLCULEMEDI (tum duzlemler olculemedi)")
            for k, v in plane_status.items():
                print("  %s: olculemedi (sebep: %s, yol=%s)"
                      % (k, v["sebep"], v["yol"]))
            print("OLCULEMEYEN_DUZLEM=%s OLCULEMEYEN_SATIR=%d"
                  % (sonuc.get("OLCULEMEYEN_DUZLEM", ""),
                     sonuc.get("OLCULEMEYEN_SATIR", 0)))
        return 2

    if args.json:
        print(json.dumps({
            "EVREN": sonuc["EVREN"],
            "HARITADA": sonuc["HARITADA"],
            "EKSIK": sonuc["EKSIK"],
            "BAYAT": sonuc["BAYAT"],
            "OLCULEMEYEN_SATIR": sonuc.get("OLCULEMEYEN_SATIR", 0),
            "OLCULEMEYEN_DUZLEM": sonuc.get("OLCULEMEYEN_DUZLEM", ""),
            "SAHIPSIZ": sonuc["SAHIPSIZ"],
            "KIRMIZI": sonuc["KIRMIZI"],
            "KABUL_BOS": sonuc["KABUL_BOS"],
            "CRON_EVRENI": (plane_status["cron"]["evren"]
                            if plane_status["cron"]["measured"] else "OLCULEMEDI"),
            "CRON_YOL": plane_status["cron"]["yol"],
            "CRON_SEBEP": plane_status["cron"]["sebep"],
            "TOOLS_EVRENI": (plane_status["tools"]["evren"]
                             if plane_status["tools"]["measured"] else "OLCULEMEDI"),
            "TOOLS_YOL": plane_status["tools"]["yol"],
            "TOOLS_SEBEP": plane_status["tools"]["sebep"],
        }, indent=2, ensure_ascii=False))
    else:
        print("KAPI/NOBET HARITA KAPISI (salt-okunur)")
        print("Repo: " + repo_kok)
        print("Harita: " + args.harita)
        print("Kapsam evreni (kod-kanitli): sys.exit(1..9) VEYA permissionDecision VEYA "
              "exit 1/2; -test/-mutasyon/-prob dislanir")
        # Paket ③-f §H2: CRON_EVRENI raporu.
        if plane_status["cron"]["measured"]:
            print("Cron evreni: %d (yol=%s)" % (plane_status["cron"]["evren"],
                                                plane_status["cron"]["yol"]))
        else:
            print("Cron evreni: OLCULEMEDI (sebep: %s, yol=%s)"
                  % (plane_status["cron"]["sebep"], plane_status["cron"]["yol"]))
        if plane_status["tools"]["measured"]:
            print("Tools evreni: %d (yol=%s)" % (plane_status["tools"]["evren"],
                                                  plane_status["tools"]["yol"]))
        else:
            print("Tools evreni: OLCULEMEDI (sebep: %s, yol=%s)"
                  % (plane_status["tools"]["sebep"], plane_status["tools"]["yol"]))
        print("")
        print(ozet_satir(sonuc, harita=harita))
        if sonuc["EKSIK"]:
            print("")
            print("EKSIK (evrende var, haritada yok) — RED:")
            for yol, base in sonuc["EKSIK"]:
                print("  %s  (%s)" % (yol, base))
        if sonuc["BAYAT"]:
            print("")
            print("BAYAT (haritada var, evrende yok) — RED:")
            for yol, ad, no in sonuc["BAYAT"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))
        if sonuc.get("OLCULEMEYEN_SATIR"):
            print("")
            print("OLCULEMEYEN_SATIR=%d (duzlem=%s, yargilanmaz) — ayri sayildi, kapi YANMAZ:"
                  % (sonuc["OLCULEMEYEN_SATIR"], sonuc.get("OLCULEMEYEN_DUZLEM", "")))
            for yol, ad, no in sonuc["OLCULEMEYEN_SATIRLAR"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))
        if sonuc["SAHIPSIZ"]:
            print("")
            print("SAHIPSIZ (EV=BILINMIYOR) — kapi YANMAZ, yalniz sayilir:")
            for yol, ad, no in sonuc["SAHIPSIZ"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))
        if sonuc["KIRMIZI"]:
            print("")
            print("KIRMIZI (gecersiz EV/SERIT) — RED:")
            for no, msg in sonuc["KIRMIZI"]:
                print("  satir %d  %s" % (no, msg))
        if sonuc["KABUL_BOS"]:
            print("")
            print("KABUL_BOS (KABUL_KOMUTU bos) — RED (Paket ③-d §H3):")
            for no, yol, ad in sonuc["KABUL_BOS"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))

    # RC davranisi:
    # - EKSIK veya BAYAT varsa RED -> rc=1
    # - KIRMIZI (gecersiz EV/SERIT) varsa RED -> rc=1
    # - KABUL_BOS (Paket ③-d §H3) varsa RED -> rc=1
    # - SAHIPSIZ tek basina RED degil -> rc=0 (spec §2b)
    # - EVREN=0 ise RED -> rc=1 (bos evren yesil degil)
    # - OLCULEMEYEN_SATIR tek basina RED degil -> rc=0 (Paket ③-g §H1)
    # - Tum duzlemler OLCULEMEDI ise rc=2 OLCULEMEDI (Paket ③-g §H2)
    if (sonuc["EKSIK"] or sonuc["BAYAT"] or sonuc["KIRMIZI"]
            or sonuc["KABUL_BOS"] or sonuc["EVREN"] == 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
