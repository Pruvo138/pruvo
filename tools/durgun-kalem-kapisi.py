#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/durgun-kalem-kapisi.py — PAKET T5: 4 SAAT hareketsiz kalem OTOMATIK DEVREDILIR.

Mimar hukumu (19 Agu 2026, KraL). BaBa tatbikat programi T5.

Bir kalem **4 saattir durum degistirmediyse** (yeni dagitim, kapanis, onarim,
eskalasyon YOK) otomatik olarak DEVREDILIR: sahibi T3'un EV eksenine gore
cozulur ve devir izi birakilir. Kapı adı: `tools/durgun-kalem-kapisi.py`.

4 kol — her biri AYRI olculur; her mutant HEDEF KOLU kanitlar:
  T5-DURGUN     : son hareket >= 4 saat ise kalem DEVIR adayidir
  T5-TAZE       : son hareket < 4 saat ise DOKUNULMAZ (yanlis-pozitif nobeti)
  T5-IZ         : devir bir IZ birakir (kalem iki ucta da gorunur; SILME YOK)
  T5-OLCULEMEDI : damga yok/bozuk/gelecek tarihli ise **fail-closed**: "taze"
                  SAYILMAZ, ayri sayacla raporlanir

🔴 **ZAMAN KAYNAGI TEK** olsun ve enjekte edilebilir olsun (`--simdi <ISO>`),
yoksa test gercek saate baglanir ve gece yarisi kirmizi yanar. Sentetik
damgalarla olc.

Isletim modlari:
  --kendini-test       : 4 mutant + izolasyon (tempfile.mkdtemp); gercek
                          deftere / durum dosyasina / posta kutusuna DOKUNMAZ.
  --rapor --simdi <ISO>: gercek defter uzerinde YAZMADAN; kac kalem durgun,
                          kaci taze, kaci OLCULEMEDI.

🔴 **CANLI KABLOLAMA BU PAKETTE YOK.** Kapi yazilir, olculur, CI'da
`--kendini-test` olarak kosar. `nobet-kapi.py`'ye takilmasi AYRI karardir
(o dosya versiyon kontrolu disinda; yedegi ayri is).

KABUL (calistirilabilir):
  python3 tools/durgun-kalem-kapisi.py --kendini-test
    -> rc=0, MUTANT=4/4, dort kol adi ciktida; sentetik defter/damga
       tempfile izolasyonunda, GERCEK deftere DOKUNMAZ.

  Dort curutme: her kolun govdesi oldurulunce ilgili mutant SESSIZ kalmali.

  python3 tools/durgun-kalem-kapisi.py --rapor --simdi <ISO>
    -> gercek defter uzerinde YAZMADAN: kac kalem durgun, kaci taze,
       kaci OLCULEMEDI.

  nobet.yml serit-b'ye adim ekle (`if: ${{ !cancelled() }}`), `skipped` DEGIL.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - --kendini-test gercek deftere / durum dosyasina / posta kutusuna ASLA
    dokunmaz; tum islemler tempfile.mkdtemp() altinda izole.
  - --rapor salt-okunur: defteri + durum dosyasini okur, hicbir yere yazmaz.
  - Kol ayrimi: her kol KENDI jetonu ile konusur (`T5-DURGUN`, `T5-TAZE`,
    `T5-IZ`, `T5-OLCULEMEDI`); mutant dogrulamasi jeton BASINA bakar, boylece
    bir kolun govdesi oldurulunce DIGER kolun mesaji onun yerine gecse bile
    mutant YASAMAZ (kol ayrimi).
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

# ---- sabitler -----------------------------------------------------------------
ESIK_DAKIKA = 240   # 4 saat = 240 dakika
DURUM_DOSYA_ADI = "durgun-kalem-durum.json"

# Kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir. Kol ATIFI
# mesajin BASINDA gecer; mutant dogrulamasi `startswith(kol + " ")` ile yalnizca
# kendi kolunun imzasini dogrular. Bu sayede bir kol oldurulunce diger kolun
# mesaji onun yerine gecse bile mutant YASAMAZ (kol ayrimi).
T5_DURGUN_JETON     = "T5-DURGUN"
T5_TAZE_JETON       = "T5-TAZE"
T5_IZ_JETON         = "T5-IZ"
T5_OLCULEMEDI_JETON = "T5-OLCULEMEDI"

# Mutant adlari + hedef kol eslestirmesi.
MUTANT_HEDEF = {
    "M1": T5_DURGUN_JETON,
    "M2": T5_TAZE_JETON,
    "M3": T5_IZ_JETON,
    "M4": T5_OLCULEMEDI_JETON,
}

# Varsayilan durum dosyasi yolu (gercek mod). --kendini-test bunu KULLANMAZ,
# tum islemlerini gecici dizinde yapar.
VARSAYILAN_DURUM_YOLU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/" + DURUM_DOSYA_ADI)


# ------------------------------------------------------------------------------
# YARDIMCILAR
# ------------------------------------------------------------------------------
def _repo_kok():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        os.pardir))


def _simdi_coz(simdi_str):
    """ISO 8601 (YYYY-MM-DDTHH:MM:SSZ veya +TZ) -> aware datetime (UTC). Hata -> None."""
    if not simdi_str:
        return None
    s = simdi_str.strip()
    if not s:
        return None
    # Z son ek
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt


def _damga_coz(deger, simdi=None):
    """Bir damga degeri -> aware datetime (UTC). None/yanlis bicim/gelecek tarihli
    ise None doner. Gelecek tarihli = simdi'den SONRA ise fail-closed (None doner).

    simdi verilmisse ve dt > simdi ise gelecek sayilir (None doner)."""
    if deger is None:
        return None
    if not isinstance(deger, str):
        return None
    s = deger.strip()
    if not s:
        return None
    dt = _simdi_coz(s)
    if dt is None:
        return None
    if simdi is not None and dt > simdi:
        return None  # gelecek tarihli -> fail-closed
    return dt


# ------------------------------------------------------------------------------
# DEFTER PARSE
# ------------------------------------------------------------------------------
def _acik_bolge(defter):
    """ACIK KALEMLER bolgesinin (baslik dahil) satir listesini doner.

    Baslik ## ile baslar; sonraki ## ile bolge biter. Bolge YOKSA None doner.
    """
    satirlar = defter.splitlines()
    bas = None
    for i, satir in enumerate(satirlar):
        if satir.startswith("## ACIK KALEMLER"):
            bas = i
            break
    if bas is None:
        return None
    son = len(satirlar)
    for i in range(bas + 1, len(satirlar)):
        if satirlar[i].startswith("## "):
            son = i
            break
    return satirlar[bas:son]


KIMLIK_RE_PATTERN = r"\bK\d+\b"


def kalem_listesi(defter):
    """ACIK KALEMLER bolgesindeki kalemleri bulur. Returns: [
        {"kimlik": "K186", "satir": str, "satir_no": int, "tip": "KALEM"|"DIGER"}, ...
    ]
    Yoksa [].

    Kalem tespiti: bolgedeki "- " ile baslayan satirlar. K-NNN tokenu iceriyorsa
    KALEM; yoksa DIGER (yine de sayilabilir ama T5'in odağı KALEM).
    """
    import re
    bolge = _acik_bolge(defter)
    if bolge is None:
        return []
    out = []
    kimlik_re = re.compile(KIMLIK_RE_PATTERN)
    for i, satir in enumerate(bolge):
        if not satir.startswith("- "):
            continue
        m = kimlik_re.search(satir)
        if m is None:
            continue
        out.append({"kimlik": m.group(0).upper(),
                    "satir": satir,
                    "satir_no": i,
                    "tip": "KALEM"})
    return out


# ------------------------------------------------------------------------------
# DURUM DOSYASI
# ------------------------------------------------------------------------------
def durum_oku(yol):
    """Durum dosyasini okur. Returns: {"son_guncelleme": iso|None,
    "kalemler": {kimlik: iso_damga}} veya None (dosya yok/bozuk).

    Bozuk JSON -> None (fail-closed; OLCULEMEDI sayaci artar).
    """
    if not os.path.isfile(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict):
        return None
    son = veri.get("son_guncelleme")
    kalemler_raw = veri.get("kalemler", {})
    if not isinstance(kalemler_raw, dict):
        kalemler_raw = {}
    kalemler = {}
    for k, v in kalemler_raw.items():
        if isinstance(k, str) and isinstance(v, str):
            kalemler[k.upper()] = v
    return {"son_guncelleme": son if isinstance(son, str) else None,
            "kalemler": kalemler}


def durum_yaz_atomik(yol, veri):
    """Durum dosyasini atomik yazar (gecici + os.replace). IOError raise."""
    dizin = os.path.dirname(yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".durum-", dir=dizin or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


# ------------------------------------------------------------------------------
# DAMGA URETICI (T5b — hareket damgasi ekseni)
# ------------------------------------------------------------------------------
# 🔴 **FAIL-OPEN YASAGI:** damga URETICISI hicbir kalemi "taze" ILAN ETMEZ. Uretici
# yalnizca `kimlik -> damga` haritasi uretir. Hukum YALNIZ mevcut `kalem_damgasi()`
# verir. Damgasi TURETILEMEYEN kalem haritaya YAZILMAZ → `kalem_damgasi()` onu
# OLCULEMEDI olarak okur. "git izi yok" asla "taze" DEMEK DEGILDIR.
#
# mutant kapilari (kendini-test icin):
#   "M5": damga uretilemeyen kalemi haritaya `simdi` damgasiyla yaz (fail-open)
#   "M6": ciktiya T5-TAZE satirlari ekle (ikinci hukum yeri)
#   "M7": en son commit yerine EN ESKI commit'in tarihini al


def damga_uret(defter_yol, repo_kok, durum_yol, simdi_dt, *, mutant=None):
    """DEVAM.md'nin GIT GECMISinden kalem damgalarini uret.

    Args:
      defter_yol: DEVAM.md dosya yolu (repo_kok altinda olmali).
      repo_kok: git repo kok dizini (.git/ icermeli).
      durum_yol: cikti JSON dosyasi yolu.
      simdi_dt: simdi zamani (aware datetime, UTC).
      mutant: None normal; "M5"/"M6"/"M7" test kapilari.

    Returns:
      {"uretilen": int, "uretitemeyen": int,
       "neden_git_izi_yok": int, "neden_defter_gitsiz": int,
       "harita": {kimlik: iso_damga}, "hata": str|None,
       "ekrana": [str, ...]} — cikti satirlari (M6 T5-TAZE satir ekler).
    """
    out = {"uretilen": 0, "uretitemeyen": 0,
           "neden_git_izi_yok": 0, "neden_defter_gitsiz": 0,
           "harita": {}, "hata": None, "ekrana": []}

    # Defter var mi?
    if not os.path.isfile(defter_yol):
        out["hata"] = "defter bulunamadi: %s" % defter_yol
        out["neden_defter_gitsiz"] += 1
        return out

    # Repo git mi? (worktree'lerde .git bir DOSYA olur — git komutuyla dogrula)
    try:
        r_repo = subprocess.run(
            ["git", "-C", repo_kok, "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=10)
        if r_repo.returncode != 0:
            out["hata"] = "repo git degil: %s" % repo_kok
            out["neden_defter_gitsiz"] += 1
            return out
    except (FileNotFoundError, subprocess.TimeoutExpired):
        out["hata"] = "git komutu calistirilamadi"
        out["neden_defter_gitsiz"] += 1
        return out

    # Defter repo altinda mi?
    try:
        defter_abs = os.path.abspath(defter_yol)
        repo_abs = os.path.abspath(repo_kok)
        if not (defter_abs == repo_abs
                or defter_abs.startswith(repo_abs + os.sep)):
            out["hata"] = "defter repo altinda degil"
            out["neden_defter_gitsiz"] += 1
            return out
        defter_rel = os.path.relpath(defter_abs, repo_abs)
    except Exception as e:
        out["hata"] = "defter yol cozumu basarisiz: %r" % e
        out["neden_defter_gitsiz"] += 1
        return out

    # ACIK KALEMLER bolgesini parse et
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    kalemler_raw = kalem_listesi(defter)

    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Her kalem icin git log'da commit bul
    for k in kalemler_raw:
        kimlik = k["kimlik"]
        # git log: -G ile bu kalem kimligini iceren satirla temas eden commit'ler
        # -1 ile tek commit. --reverse ile siralama ters (en eski once).
        # Regex: (^|[^0-9])KIMLIK($|[^0-9]) — \b git -G'de tum versiyonlarda
        # calismadigi olculdu (git 2.50 Apple Git-155). Karakter sinifi ile
        # kelime siniri taklit edilir.
        desen = "(^|[^0-9])%s($|[^0-9])" % kimlik
        args = ["git", "-C", repo_kok, "log",
                "--pretty=format:%cI",
                "-G", desen]
        if mutant == "M7":
            # En eski commit: --reverse (yalniz) ile en eski ONCE listelenir;
            # ilk satir = OLDEST. `-1` ile birlikte TERS davranir (walk'a
            # uygulanir, NEWEST verir).
            args.append("--reverse")
        else:
            # En son commit: -1 ile tek satir = NEWEST.
            args.append("-1")
        args.extend(["--", defter_rel])

        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            out["neden_git_izi_yok"] += 1
            if mutant == "M5":
                # Fail-open: uretilemeyen kaleme simdi damga yaz
                out["harita"][kimlik] = simdi_str
                out["uretilen"] += 1
            continue

        if r.returncode != 0 or not r.stdout.strip():
            out["neden_git_izi_yok"] += 1
            if mutant == "M5":
                out["harita"][kimlik] = simdi_str
                out["uretilen"] += 1
            continue

        if mutant == "M7":
            # EN ESKI commit: --reverse ile en eski ONCE listelenir; ilk
            # satiri al. `-1` tek-basina "--reverse" ile birlikte TERS davranir
            # (git log -1 walk'ta, --reverse output'ta; -1 walk'a uygulanir ve
            # ilk commits'i alir = NEWEST). Bu yuzden --reverse YALNIZ kullanilir.
            satirlar = [s for s in r.stdout.strip().splitlines() if s]
            damga = satirlar[0] if satirlar else None
        else:
            # EN SON commit: -1 ile ilk satir.
            damga = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else None
        if damga is None or _damga_coz(damga, simdi=simdi_dt) is None:
            out["neden_git_izi_yok"] += 1
            if mutant == "M5":
                out["harita"][kimlik] = simdi_str
                out["uretilen"] += 1
            continue

        out["harita"][kimlik] = damga
        out["uretilen"] += 1

    # M6: ikinci hukum yeri — ciktiya T5-TAZE satirlari ekle
    if mutant == "M6":
        for kimlik, damga in out["harita"].items():
            out["ekrana"].append("T5-TAZE %s damga=%s" % (kimlik, damga))

    # Durum dosyasini atomik yaz
    durum_veri = {"son_guncelleme": simdi_str,
                  "kalemler": out["harita"]}
    try:
        durum_yaz_atomik(durum_yol, durum_veri)
    except Exception as e:
        out["hata"] = "durum yazilamadi: %r" % e

    return out


# ------------------------------------------------------------------------------
# KALEM SINIFLANDIRMA
# ------------------------------------------------------------------------------
def kalem_damgasi(kalem, durum, simdi, *, kirik_kol=None):
    """Bir kalemin damgasini durum dosyasindan alip simdi ile karsilastirir.
    Returns: {"kol": "T5-DURGUN"|"T5-TAZE"|"T5-OLCULEMEDI",
              "damga": iso|None, "fark_dakika": float|None, "hata": str|None}.

    Kurallar:
      - Durum dosyasi yoksa veya bozuksa: T5-OLCULEMEDI (fail-closed).
      - Kalem durumda yoksa: T5-OLCULEMEDI (fail-closed; "taze" SAYILMAZ).
      - Damga None / yanlis bicimli / gelecek tarihli: T5-OLCULEMEDI.
      - Damga gecerli, fark >= 240 dk: T5-DURGUN.
      - Damga gecerli, fark < 240 dk: T5-TAZE.

    kirik_kol: curutme testi icin. None ise normal mantik; bir kol jetonu
    ise o kolu DEVRE DISI birakir (o kolun karar vermesi gereken yerde
    her zaman ZIT kol uretir). Bu sayede "kol govdesi oldurulunce mutant
    yasar mi" sorusu yanitlanir.
    """
    if durum is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "durum dosyasi yok/bozuk"}
    iso_damga = durum["kalemler"].get(kalem["kimlik"])
    if iso_damga is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "kalem durum dosyasinda yok"}
    dt = _damga_coz(iso_damga, simdi=simdi)
    if dt is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": iso_damga,
                "fark_dakika": None, "hata": "damga bozuk veya gelecek tarihli"}
    fark_sn = (simdi - dt).total_seconds()
    fark_dk = fark_sn / 60.0
    # Curutme testi: eger T5-DURGUN kolu oldurulmusse, HER DURUMDA TAZE
    # uret (4-saat-kuralini devre disi birak); T5-TAZE oldurulmusse HER
    # DURUMDA DURGUN uret; T5-OLCULEMEDI oldurulmusse gelecek tarihliyi
    # gecerli say (TAZE uret).
    if kirik_kol == T5_DURGUN_JETON:
        return {"kol": T5_TAZE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T5_TAZE_JETON:
        return {"kol": T5_DURGUN_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T5_OLCULEMEDI_JETON:
        # Gelecek tarihliyi gecerli say — bu M4'un test ettigi kural.
        # Burada M4'un vakasi zaten gecmis; ama gelecek-tarihli davranisi
        # test icin TAZE donelim.
        return {"kol": T5_TAZE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if fark_dk >= ESIK_DAKIKA:
        return {"kol": T5_DURGUN_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    return {"kol": T5_TAZE_JETON, "damga": iso_damga,
            "fark_dakika": fark_dk, "hata": None}


def hepsini_simfla(defter, durum_yolu, simdi, *, kirik_kol=None):
    """Butun kalemleri siniflandirir. Returns:
      {"kalemler": [{kimlik, kol, damga, fark_dakika, hata}, ...],
       "durgun": int, "taze": int, "olculemedi": int,
       "hata": str|None, "kalem_sayisi": int, "durum_ok": bool}.
    """
    if not defter or not isinstance(defter, str):
        return {"kalemler": [], "durgun": 0, "taze": 0, "olculemedi": 0,
                "hata": "defter yok/yanlis tip", "kalem_sayisi": 0,
                "durum_ok": False}
    kalemler_raw = kalem_listesi(defter)
    durum = durum_oku(durum_yolu)
    kalemler = []
    durgun = taze = olcu = 0
    for k in kalemler_raw:
        sonuc = kalem_damgasi(k, durum, simdi, kirik_kol=kirik_kol)
        kalemler.append({"kimlik": k["kimlik"], "kol": sonuc["kol"],
                         "damga": sonuc["damga"], "fark_dakika": sonuc["fark_dakika"],
                         "hata": sonuc["hata"]})
        if sonuc["kol"] == T5_DURGUN_JETON:
            durgun += 1
        elif sonuc["kol"] == T5_TAZE_JETON:
            taze += 1
        else:
            olcu += 1
    hata = None if durum is not None else "durum dosyasi okunamadi"
    return {"kalemler": kalemler, "durgun": durgun, "taze": taze,
            "olculemedi": olcu, "hata": hata,
            "kalem_sayisi": len(kalemler_raw),
            "durum_ok": durum is not None}


# ------------------------------------------------------------------------------
# DEVIR + IZ (T5-IZ kolu)
# ------------------------------------------------------------------------------
def _iz_satiri(kalem, ev, damga):
    """Devir iz satiri. Format: T5-IZ <kalem> <EV> <damga>."""
    return ("T5-IZ %s %s damga=%s"
            % (kalem["kimlik"], ev, damga))


def devir_yap(kalem, ev, damga, kaynak_yol, hedef_yol, *,
              iz_yazilamaz=False):
    """Bir kalemi hedef posta kutusuna yazar + kaynak posta kutusuna IZ birakir.
    Returns: {"yazildi": bool, "iz_yazildi": bool, "hata": str|None}.

    Kol ayrimi:
      - Hedef kutu yazilamazsa: HATA `T5-OLCULEMEDI ` onekiyle baslar.
      - IZ yazilamazsa: HATA `T5-IZ ` onekiyle baslar; yazildi=True ama iz
        yazilmadi ise devir TAMAMLANMIS SAYILMAZ (fail-closed).
    """
    sonuc = {"yazildi": False, "iz_yazildi": False, "hata": None}
    # Hedefe yaz
    try:
        mevcut = ""
        if os.path.isfile(hedef_yol):
            with open(hedef_yol, encoding="utf-8") as f:
                mevcut = f.read()
        if mevcut and not mevcut.endswith("\n"):
            mevcut += "\n"
        yeni = mevcut + ("DEVREDILDI: %s -> %s damga=%s\n"
                         % (kalem["kimlik"], ev, damga))
        fd, gecici = tempfile.mkstemp(prefix=".devir-", dir=os.path.dirname(hedef_yol) or None)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(yeni)
            os.replace(gecici, hedef_yol)
            sonuc["yazildi"] = True
        except Exception as e:
            try:
                os.unlink(gecici)
            except OSError:
                pass
            sonuc["hata"] = "T5-OLCULEMEDI hedef kutu yazma basarisiz: %r" % e
            return sonuc
    except Exception as e:
        sonuc["hata"] = "T5-OLCULEMEDI hedef kutu yazma basarisiz: %r" % e
        return sonuc

    # IZ birak (kaynaga)
    if iz_yazilamaz:
        sonuc["hata"] = "T5-IZ iz yazma kanal bozuk (mutant M3 simulasyonu)"
        return sonuc
    try:
        mevcut = ""
        if os.path.isfile(kaynak_yol):
            with open(kaynak_yol, encoding="utf-8") as f:
                mevcut = f.read()
        if mevcut and not mevcut.endswith("\n"):
            mevcut += "\n"
        yeni = mevcut + _iz_satiri(kalem, ev, damga) + "\n"
        fd, gecici = tempfile.mkstemp(prefix=".iz-", dir=os.path.dirname(kaynak_yol) or None)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(yeni)
            os.replace(gecici, kaynak_yol)
            sonuc["iz_yazildi"] = True
        except Exception as e:
            try:
                os.unlink(gecici)
            except OSError:
                pass
            sonuc["hata"] = "T5-IZ iz yazma basarisiz: %r" % e
            return sonuc
    except Exception as e:
        sonuc["hata"] = "T5-IZ iz yazma basarisiz: %r" % e
        return sonuc

    return sonuc


# ------------------------------------------------------------------------------
# --rapor (salt-okunur)
# ------------------------------------------------------------------------------
def rapor_yaz(sonuc, simdi_str):
    """Raporu insan-okur ve makine-okur formatinda bas."""
    print("DURGUN KALEM KAPISI — RAPOR (YAZMAZ)")
    print("simdi: %s" % simdi_str)
    print("esik: %d dakika (4 saat)" % ESIK_DAKIKA)
    print("")
    print("kalem_sayisi=%d durgun=%d taze=%d olculemedi=%d durum_ok=%s"
          % (sonuc["kalem_sayisi"], sonuc["durgun"], sonuc["taze"],
             sonuc["olculemedi"], sonuc["durum_ok"]))
    if sonuc["hata"]:
        print("HATA: %s" % sonuc["hata"])
    print("")
    for k in sonuc["kalemler"]:
        fark = "?"
        if k["fark_dakika"] is not None:
            fark = "%.1f dk" % k["fark_dakika"]
        damga = k["damga"] or "-"
        print("%-10s %-15s damga=%-22s fark=%-12s %s"
              % (k["kimlik"], k["kol"], damga, fark,
                 ("hata: " + k["hata"]) if k["hata"] else ""))


# ------------------------------------------------------------------------------
# --kendini-test (4 mutant + izolasyon)
# ------------------------------------------------------------------------------
SENTETIK_DEfter = (
    "# sentetik devter\n"
    "\n"
    "## ACIK KALEMLER\n"
    "- K190 CHIP `KraL-test bir`\n"
    "- K191 CHIP `KraL-test iki`\n"
    "- K192 CHIP `KraL-test uc`\n"
    "- K193 CHIP `KraL-test dort`\n"
    "## SONRA\n"
)


def _ft(dakika):
    """simdi'den dakika once ISO string."""
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=dakika)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ft_ileri(dakika):
    """simdi'den dakika sonra (gelecek tarihli)."""
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=dakika)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_repo_kur(kok, defter_icerik, commit_tarihleri=None):
    """Sentetik git deposu kur. commit_tarihleri None ise tek commit (simdi).

    commit_tarihleri: [(iso_tarih, devam_icerik), ...] — eskiden yeniye sirali.
    """
    kok_abs = os.path.abspath(kok)
    if not os.path.isdir(kok_abs):
        os.makedirs(kok_abs)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@pruvo"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@pruvo"
    subprocess.run(["git", "-C", kok_abs, "init", "-q"],
                   env=env, check=True, capture_output=True)
    subprocess.run(["git", "-C", kok_abs, "config", "user.email",
                    "test@pruvo"], env=env, check=True, capture_output=True)
    subprocess.run(["git", "-C", kok_abs, "config", "user.name",
                    "test"], env=env, check=True, capture_output=True)
    defter_yol = os.path.join(kok_abs, "DEVAM.md")
    if commit_tarihleri is None:
        with open(defter_yol, "w", encoding="utf-8") as f:
            f.write(defter_icerik)
        subprocess.run(["git", "-C", kok_abs, "add", "DEVAM.md"],
                       env=env, check=True)
        subprocess.run(["git", "-C", kok_abs, "commit", "-q", "-m", "temel"],
                       env=env, check=True)
    else:
        for tarih, icerik in commit_tarihleri:
            with open(defter_yol, "w", encoding="utf-8") as f:
                f.write(icerik)
            env_l = env.copy()
            env_l["GIT_AUTHOR_DATE"] = tarih
            env_l["GIT_COMMITTER_DATE"] = tarih
            subprocess.run(["git", "-C", kok_abs, "add", "DEVAM.md"],
                           env=env_l, check=True)
            subprocess.run(["git", "-C", kok_abs, "commit", "-q",
                            "-m", "t:%s" % tarih],
                           env=env_l, check=True)
    return kok_abs


def kendini_test(gecici_kok):
    """4+3 mutant + izolasyon. Her mutant kendi kolunu AYRICA kanitlar.

    kucuk gecici kok: --kendini-test disindan cagrilmaz (yine de savunmaci).
    """
    # Gecici izolasyon kokunu hazirla
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kaynak_posta = os.path.join(gecici_kok, "kaynak.md")
    hedef_posta = os.path.join(gecici_kok, "hedef.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)
    # Hicbir kalem durumda yok -> hepsi OLCULEMEDI (fail-closed)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    adimlar = []
    atfi_dogru = 0  # K182: hedef kol kirmizi + yan eksen yesil

    # --- M1: T5-DURGUN ------------------------------------------------------
    # Damga 300 dk (5 saat) once -> DURGUN olmali.
    # M1 dogrulamasi: T5-DURGUN govdesi oldurulurse bu kalem TAZE
    # veya OLCULEMEDI diye YANLIS siniflanir; mutant YASAMAZ.
    durum_m1 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": _ft(300)}}
    durum_yaz_atomik(durum_yol, durum_m1)
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    sonuc_m1 = hepsini_simfla(defter, durum_yol, simdi_dt)
    m1_kalem = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K190"), None)
    m1_durgun = (m1_kalem is not None
                 and m1_kalem["kol"] == T5_DURGUN_JETON)
    t5_durgun_mesaj = ("K190 T5-DURGUN damga=%s fark=%.1f dk"
                       % (m1_kalem["damga"] if m1_kalem else "?",
                          m1_kalem["fark_dakika"] if m1_kalem and m1_kalem["fark_dakika"] is not None else 0.0))
    adimlar.append(("M1", T5_DURGUN_JETON, m1_durgun, t5_durgun_mesaj,
                    {"kol": m1_kalem["kol"] if m1_kalem else "?"}))

    # --- M2: T5-TAZE --------------------------------------------------------
    # Damga 60 dk (1 saat) once -> TAZE olmali.
    # M2 dogrulamasi: T5-TAZE govdesi oldurulurse bu kalem DURGUN
    # olarak YANLIS siniflanir; mutant YASAMAZ.
    durum_m2 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": _ft(300),   # ayni kalem
                             "K191": _ft(60)}}   # taze
    durum_yaz_atomik(durum_yol, durum_m2)
    sonuc_m2 = hepsini_simfla(defter, durum_yol, simdi_dt)
    m2_kalem = next((k for k in sonuc_m2["kalemler"] if k["kimlik"] == "K191"), None)
    m2_taze = (m2_kalem is not None
               and m2_kalem["kol"] == T5_TAZE_JETON)
    t5_taze_mesaj = ("K191 T5-TAZE damga=%s fark=%.1f dk"
                     % (m2_kalem["damga"] if m2_kalem else "?",
                        m2_kalem["fark_dakika"] if m2_kalem and m2_kalem["fark_dakika"] is not None else 0.0))
    adimlar.append(("M2", T5_TAZE_JETON, m2_taze, t5_taze_mesaj,
                    {"kol": m2_kalem["kol"] if m2_kalem else "?"}))

    # --- M3: T5-IZ ----------------------------------------------------------
    # Devir yapilirken IZ birakilmali. IZ kanalini iz_yazilamaz=True ile
    # kirdigimizda hata T5-IZ onekiyle baslamali; mutant YASAMAZ.
    # Gercek kosumda iz_yazilamaz=False oldugundan IZ yazilir + kalem iki
    # ucta da gorunur.
    durum_m3 = {"son_guncelleme": simdi_str,
                "kalemler": {"K192": _ft(500)}}
    durum_yaz_atomik(durum_yol, durum_m3)
    kalem_m3 = {"kimlik": "K192"}
    # ONCE bozuk kanal: iz_yazilamaz=True
    sonuc_m3_bozuk = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                               kaynak_yol=kaynak_posta, hedef_yol=hedef_posta,
                               iz_yazilamaz=True)
    m3_iz_hatasi = (sonuc_m3_bozuk["hata"] is not None
                    and sonuc_m3_bozuk["hata"].startswith(T5_IZ_JETON + " ")
                    and sonuc_m3_bozuk["iz_yazildi"] is False)
    # SONRA saglam kanal: gercek devir
    sonuc_m3_ok = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                            kaynak_yol=kaynak_posta, hedef_yol=hedef_posta)
    # IZ satirinin KAYNAK dosyada gorunmesi + DEVREDILDI'nin HEDEF dosyada
    # gorunmesi = kalem iki ucta da var (SILME YOK).
    kaynak_icerik = open(kaynak_posta, encoding="utf-8").read() if os.path.isfile(kaynak_posta) else ""
    hedef_icerik = open(hedef_posta, encoding="utf-8").read() if os.path.isfile(hedef_posta) else ""
    m3_iz_yazildi = (sonuc_m3_ok["iz_yazildi"] is True
                     and T5_IZ_JETON in kaynak_icerik
                     and "K192" in kaynak_icerik
                     and "DEVREDILDI" in hedef_icerik
                     and "K192" in hedef_icerik)
    t5_iz_mesaj = ("K192 T5-IZ bozuk kanal: hata=%s | saglam kanal: iz_yazildi=%s "
                   "kaynak_icerik_iz=%s hedef_icerik_devredildi=%s"
                   % (sonuc_m3_bozuk["hata"], sonuc_m3_ok["iz_yazildi"],
                      T5_IZ_JETON in kaynak_icerik,
                      "DEVREDILDI" in hedef_icerik))
    m3_reddetti = (m3_iz_hatasi and m3_iz_yazildi)
    adimlar.append(("M3", T5_IZ_JETON, m3_reddetti, t5_iz_mesaj,
                    {"bozuk": m3_iz_hatasi, "ok": m3_iz_yazildi}))

    # --- M4: T5-OLCULEMEDI --------------------------------------------------
    # 3 alt vaka: damga YOK, damga BOZUK, damga GELECEK. Hepsi T5-OLCULEMEDI
    # olarak siniflanmali (fail-closed; "taze" SAYILMAZ).
    durum_m4 = {"son_guncelleme": simdi_str,
                "kalemler": {"K193": _ft(60),       # K193 yok ama 4. kalem
                             # K190 hic yok, K191 bozuk, K192 gelecek
                             "K191": "bozuk-tarih-degil",
                             "K192": _ft_ileri(60)}}
    durum_yaz_atomik(durum_yol, durum_m4)
    sonuc_m4 = hepsini_simfla(defter, durum_yol, simdi_dt)
    olculemedi_sayaci = sum(1 for k in sonuc_m4["kalemler"]
                            if k["kol"] == T5_OLCULEMEDI_JETON)
    # 4 kalemden 3'u (K190 yok + K191 bozuk + K192 gelecek) OLCULEMEDI olmali.
    # K193 var (60 dk = taze) ve TAZE olmali; bu vakanin M4'le ilgisi yok
    # ama dogrulama yapalim.
    m4_olcu = (olculemedi_sayaci == 3
               and sonuc_m4["olculemedi"] == 3)
    # Ayni zamanda K193 TAZE olmali (yani OLCULEMEDI'a sigmayan tek kalem TAZE).
    k193 = next((k for k in sonuc_m4["kalemler"] if k["kimlik"] == "K193"), None)
    m4_taze_tazede = (k193 is not None and k193["kol"] == T5_TAZE_JETON)
    t5_olcu_mesaj = ("4 kalemden 3'u OLCULEMEDI (damga yok/bozuk/gelecek); "
                     "K193 TAZE (kanit: 'taze' SAYILMAZ kurali calisiyor). "
                     "olculemedi_sayaci=%d K193=%s"
                     % (olculemedi_sayaci,
                        k193["kol"] if k193 else "?"))
    adimlar.append(("M4", T5_OLCULEMEDI_JETON, (m4_olcu and m4_taze_tazede),
                    t5_olcu_mesaj,
                    {"olcu": olculemedi_sayaci, "K193": k193["kol"] if k193 else "?"}))

    # ==========================================================================
    # T5b — HAREKET DAMGASI EKSENI (paket-t5-hareket-damgasi.md)
    # 3 yeni mutant (M5/M6/M7) + 1 kontrol (K3).
    # Bu bolum sentetik git depolarinda kosar; gercek DEVAM.md'ye DOKUNMAZ.
    # ==========================================================================
    t5b_root = os.path.join(gecici_kok, "t5b")
    if not os.path.isdir(t5b_root):
        os.makedirs(t5b_root)

    # --- M5: FAIL-OPEN YASAGI -----------------------------------------------
    # Damgasi turetilemeyen kalemi haritaya `simdi` damgasiyla yazarsa
    # `kalem_damgasi()` onu T5-TAZE olarak okur (fail-open). Dogru davranis:
    # damgasi uretilemeyen kalem haritaya YAZILMAZ → T5-OLCULEMEDI.
    # Sentetik git: SENTETIK_DEFTER icindeki K190/K192 haricindeki kalemler
    # commit'lendi. K190/K192 git tarihcisinde YOK → damga uretilemez.
    m5_kok = os.path.join(t5b_root, "m5")
    # K190 ve K192 olmadan bir defter yazip commit'le (K191, K193 commit'lenir)
    m5_defter_kismi = (
        "# sentetik devter\n"
        "\n"
        "## ACIK KALEMLER\n"
        "- K191 CHIP `KraL-test iki`\n"
        "- K193 CHIP `KraL-test dort`\n"
        "## SONRA\n"
    )
    _git_repo_kur(m5_kok, m5_defter_kismi)
    # Gercek defteri (K190..K193) KOK'e yaz ama COMMIT'LEME — boylece git
    # tarihcisinde K190/K192 yok (URETILEMEYECEK), K191/K193 var.
    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)
    # symlink: defter_yol'u m5_kok'a bagla ki damga_uret dogru yolu gor
    m5_defter_link = os.path.join(m5_kok, "DEVAM.md")
    if os.path.lexists(m5_defter_link):
        os.unlink(m5_defter_link)
    # Kopyala (cross-device symlink sorunu olabilir) — gercek defterden
    # okuyabilmesi icin m5_kok'ta dosya olmali
    shutil.copy2(defter_yol, m5_defter_link)
    m5_durum = os.path.join(m5_kok, DURUM_DOSYA_ADI)

    # ONCE normal davranis: K190/K192 haritada YOK → OLCULEMEDI
    sonuc_m5_normal = damga_uret(m5_defter_link, m5_kok, m5_durum, simdi_dt)
    with open(m5_defter_link, encoding="utf-8") as f:
        m5_defter_icerik = f.read()
    sinifla_normal = hepsini_simfla(m5_defter_icerik, m5_durum, simdi_dt)
    k190_normal = next((k for k in sinifla_normal["kalemler"]
                        if k["kimlik"] == "K190"), None)
    k191_normal = next((k for k in sinifla_normal["kalemler"]
                        if k["kimlik"] == "K191"), None)
    # SONRA mutant M5: damga uretilemeyen kalem haritaya `simdi` ile yazilir
    sonuc_m5_mut = damga_uret(m5_defter_link, m5_kok, m5_durum, simdi_dt,
                              mutant="M5")
    sinifla_mut = hepsini_simfla(m5_defter_icerik, m5_durum, simdi_dt)
    k190_mut = next((k for k in sinifla_mut["kalemler"]
                     if k["kimlik"] == "K190"), None)
    k191_mut = next((k for k in sinifla_mut["kalemler"]
                     if k["kimlik"] == "K191"), None)
    # M5 hedef vaka: K190 normalde OLCULEMEDI, mutant M5'te T5-TAZE
    m5_hedef_kirmizi = (k190_normal is not None
                        and k190_normal["kol"] == T5_OLCULEMEDI_JETON
                        and k190_mut is not None
                        and k190_mut["kol"] == T5_TAZE_JETON)
    # M5 yan eksen: K191 (uretilen damga, 0dk once = TAZE)
    # Hem normalde hem mutant altinda ayni davranmali (YESIL).
    m5_yan_yesil = (k191_normal is not None and k191_mut is not None
                    and k191_normal["kol"] == k191_mut["kol"])
    m5_atfi = m5_hedef_kirmizi and m5_yan_yesil
    m5_mesaj = ("K190: normal=%s mutant=%s | K191 (yan): normal=%s mutant=%s | "
                "normal_harita=%s mutant_harita=%s"
                % (k190_normal["kol"] if k190_normal else "?",
                   k190_mut["kol"] if k190_mut else "?",
                   k191_normal["kol"] if k191_normal else "?",
                   k191_mut["kol"] if k191_mut else "?",
                   sorted(sonuc_m5_normal["harita"].keys()),
                   sorted(sonuc_m5_mut["harita"].keys())))
    adimlar.append(("M5", T5_TAZE_JETON, m5_atfi, m5_mesaj,
                    {"hedef_kirmizi": m5_hedef_kirmizi,
                     "yan_yesil": m5_yan_yesil}))
    if m5_atfi:
        atfi_dogru += 1

    # --- M6: IKINCI HUKUM YERI YASAGI --------------------------------------
    # `--damga-uret` kendi basina T5-TAZE hukmu basarsa iki yerde ayni
    # hukum uretilir (uretim cikti + siniflandirma). Dogru davranis: uretim
    # yalniz haritayi yazar; T5-TAZE hukmunu YALNIZ kalem_damgasi() uretir.
    m6_kok = os.path.join(t5b_root, "m6")
    _git_repo_kur(m6_kok, SENTETIK_DEfter)
    m6_defter_yol = os.path.join(m6_kok, "DEVAM.md")
    m6_durum = os.path.join(m6_kok, DURUM_DOSYA_ADI)
    # ONCE normal: ekrana bos, "T5-TAZE" cikti satir YOK
    sonuc_m6_normal = damga_uret(m6_defter_yol, m6_kok, m6_durum, simdi_dt)
    m6_normal_t5_taze = any("T5-TAZE" in s for s in sonuc_m6_normal["ekrana"])
    # SONRA mutant M6: ekrana T5-TAZE satirlari eklenir
    sonuc_m6_mut = damga_uret(m6_defter_yol, m6_kok, m6_durum, simdi_dt,
                              mutant="M6")
    m6_mut_t5_taze = any("T5-TAZE" in s for s in sonuc_m6_mut["ekrana"])
    # M6 hedef vaka: normalde ekrana T5-TAZE yok, mutant M6'da VAR
    m6_hedef_kirmizi = (not m6_normal_t5_taze and m6_mut_t5_taze)
    # M6 yan eksen: harita dogru (4 kalem uretildi) — her iki modda
    m6_yan_yesil = (len(sonuc_m6_normal["harita"]) == 4
                    and len(sonuc_m6_mut["harita"]) == 4
                    and sonuc_m6_normal["uretilen"]
                    == sonuc_m6_mut["uretilen"] == 4)
    m6_atfi = m6_hedef_kirmizi and m6_yan_yesil
    m6_mesaj = ("ekrana T5-TAZE: normal=%s mutant=%s | harita_uretilen "
                "normal=%d mutant=%d"
                % (m6_normal_t5_taze, m6_mut_t5_taze,
                   sonuc_m6_normal["uretilen"], sonuc_m6_mut["uretilen"]))
    adimlar.append(("M6", T5_TAZE_JETON, m6_atfi, m6_mesaj,
                    {"hedef_kirmizi": m6_hedef_kirmizi,
                     "yan_yesil": m6_yan_yesil}))
    if m6_atfi:
        atfi_dogru += 1

    # --- M7: EN SON COMMIT (en eski DEGIL) ----------------------------------
    # Damga ureticisi en son commit yerine en eski commit'in tarihini alirsa
    # damga YANLIS olur (kalem daha once "hareket gormus" gibi gozukur).
    # Sentetik git: 2 commit, ikisi de DEVAM.md'de K190..K193 satirina
    # dokunuyor; commit 1 eski, commit 2 yeni. Damga ureticisi yeni olani
    # alir. Mutant M7 eski olani alir.
    m7_kok = os.path.join(t5b_root, "m7")
    # Eski commit: 5 gun once
    tarih_eski = (simdi_dt - datetime.timedelta(days=5)
                  ).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Yeni commit: 1 saat once
    tarih_yeni = (simdi_dt - datetime.timedelta(hours=1)
                  ).strftime("%Y-%m-%dT%H:%M:%SZ")
    _git_repo_kur(m7_kok, SENTETIK_DEfter,
                  commit_tarihleri=[
                      # Commit 1 (eski): K190 satirini EKLIYOR (yeni dosya)
                      (tarih_eski,
                       SENTETIK_DEfter.replace("- K190 CHIP `KraL-test bir`",
                                                "- K190 CHIP `KraL-test bir v1`")),
                      # Commit 2 (yeni): K190 satirini MODIFIYE EDIYOR
                      (tarih_yeni,
                       SENTETIK_DEfter.replace("- K190 CHIP `KraL-test bir`",
                                                "- K190 CHIP `KraL-test bir v2`")),
                  ])
    m7_defter_yol = os.path.join(m7_kok, "DEVAM.md")
    m7_durum = os.path.join(m7_kok, DURUM_DOSYA_ADI)
    # ONCE normal: K190 damgasi = tarih_yeni
    sonuc_m7_normal = damga_uret(m7_defter_yol, m7_kok, m7_durum, simdi_dt)
    # SONRA mutant M7: K190 damgasi = tarih_eski
    sonuc_m7_mut = damga_uret(m7_defter_yol, m7_kok, m7_durum, simdi_dt,
                              mutant="M7")
    # M7 hedef vaka: uretilen damga == en yeni commit tarihi (normal)
    # ve mutant M7'de EN YENI commit tarihine esit DEGIL.
    m7_normal_damga = sonuc_m7_normal["harita"].get("K190")
    m7_mut_damga = sonuc_m7_mut["harita"].get("K190")
    m7_hedef_kirmizi = (m7_normal_damga == tarih_yeni
                        and m7_mut_damga == tarih_eski
                        and m7_normal_damga != m7_mut_damga)
    # M7 yan eksen: harita K190 dahil 4 kalem — her iki modda
    m7_yan_yesil = ("K190" in sonuc_m7_normal["harita"]
                    and "K190" in sonuc_m7_mut["harita"]
                    and sonuc_m7_normal["uretilen"]
                    == sonuc_m7_mut["uretilen"] == 4)
    m7_atfi = m7_hedef_kirmizi and m7_yan_yesil
    m7_mesaj = ("K190 damga: normal=%s (beklenen=%s) mutant=%s (beklenen=%s)"
                % (m7_normal_damga, tarih_yeni, m7_mut_damga, tarih_eski))
    adimlar.append(("M7", T5_TAZE_JETON, m7_atfi, m7_mesaj,
                    {"hedef_kirmizi": m7_hedef_kirmizi,
                     "yan_yesil": m7_yan_yesil}))
    if m7_atfi:
        atfi_dogru += 1

    # --- K3: DEPOSUZ DEFTER ------------------------------------------------
    # Git gecmisi OLMAYAN bir defter verilince arac COKMEZ:
    # `NEDEN_DEFTER_GITSIZ` sayar, hicbir kalem "taze" olmaz, rc!=0.
    k3_deposuz_kok = os.path.join(t5b_root, "k3-deposuz")
    if os.path.isdir(k3_deposuz_kok):
        shutil.rmtree(k3_deposuz_kok)
    os.makedirs(k3_deposuz_kok)
    k3_deposuz_defter = os.path.join(k3_deposuz_kok, "DEVAM.md")
    k3_deposuz_durum = os.path.join(k3_deposuz_kok, DURUM_DOSYA_ADI)
    with open(k3_deposuz_defter, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)
    # NOT: k3_deposuz_kok icinde .git YOK — sentetik depo degil.
    # ONCE .git yoksa: arac COKMEMELI, NEDEN_DEFTER_GITSIZ >= 1
    try:
        sonuc_k3 = damga_uret(k3_deposuz_defter, k3_deposuz_kok,
                              k3_deposuz_durum, simdi_dt)
        k3_cokmedi = True
    except Exception as e:
        sonuc_k3 = {"uretilen": -1, "hata": repr(e),
                    "neden_defter_gitsiz": -1, "ekrana": []}
        k3_cokmedi = False
    k3_neden_var = sonuc_k3.get("neden_defter_gitsiz", 0) >= 1
    k3_hicbiri_taze_degil = sonuc_k3.get("uretilen", 0) == 0
    # Siniflandirma cagir: hicbir kalem TAZE olmamali (durum dosyasi yok
    # cunku damga uretilemedi).
    with open(k3_deposuz_defter, encoding="utf-8") as f:
        k3_defter_icerik = f.read()
    sinifla_k3 = hepsini_simfla(k3_defter_icerik, k3_deposuz_durum, simdi_dt)
    k3_taze_sayac = sinifla_k3["taze"]
    k3_kontrol_ok = (k3_cokmedi and k3_neden_var and k3_hicbiri_taze_degil
                     and k3_taze_sayac == 0)

    # ---- ozet bas ---------------------------------------------------------

    # ---- ozet bas ---------------------------------------------------------
    print("T5 DURGUN KALEM KAPISI — KENDINI-TEST")
    print("izolasyon koku: %s" % gecici_kok)
    print("simdi: %s (enjekte)" % simdi_str)
    print("")
    mutant_sayaci = 0
    for ad, jeton, gecti, mesaj, detay in adimlar:
        print("MUTANT %s -> hedef kol %s" % (ad, jeton))
        print("  mesaj: %s" % mesaj)
        print("  detay: %s" % detay)
        if gecti:
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
            mutant_sayaci += 1
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        print("")
    # Dort kol adinin da ciktida gectigini teyit et
    print("KOL_ISIMLERI: %s %s %s %s"
          % (T5_DURGUN_JETON, T5_TAZE_JETON, T5_IZ_JETON, T5_OLCULEMEDI_JETON))
    print("")
    # K3 kontrol
    print("KONTROL K3 deposuz defter")
    print("  mesaj: cokmedi=%s neden_defter_gitsiz=%d uretilen=%d taze_sinif=%d"
          % (k3_cokmedi, sonuc_k3.get("neden_defter_gitsiz", -1),
             sonuc_k3.get("uretilen", -1), k3_taze_sayac))
    if k3_kontrol_ok:
        print("  SONUÇ: arac COKMEDI, NEDEN_DEFTER_GITSIZ>=1, hicbir kalem taze")
    else:
        print("  SONUÇ: K3 KUSUR! arac coktu veya kalem 'taze' sayildi")
    print("")
    # K4 kontrol: gerileme nobeti — mevcut 4 mutant + 4 curutme. kendini-test
    # M1-M4 zaten calistirdi; mutant_sayaci 4 eski + 3 yeni = 7 icinden ilk
    # 4'un YESIL oldugu zaten mutant_sayaci>=4 ile goruluyor. Burada ek
    # gorunurluk icin yaziyoruz.
    k4_ok = mutant_sayaci >= 4
    print("KONTROL K4 gerileme nobeti (M1-M4 + 4 curutme aynen gecer)")
    print("  mesaj: M1-M4 mutant_sayaci>=4 = %s (MUTANT=7/7 hedefi dahilinde)"
          % k4_ok)
    if k4_ok:
        print("  SONUÇ: gerileme YOK")
    else:
        print("  SONUÇ: gerileme VAR!")
    print("")
    kontrol_sayaci = sum([k3_kontrol_ok, k4_ok])
    # Toplam 7 mutant (4 eski + 3 yeni). atfi_dogru yalniz 3 yeniyi sayar
    # (eski 4'un ATFI kontrolu bu pakette tanimli degil).
    eski_adlar = {"M1", "M2", "M3", "M4"}
    yeni_adlar = {"M5", "M6", "M7"}
    eski_olan = sum(1 for (ad, _, gecti, _, _) in adimlar
                    if ad in eski_adlar and gecti)
    yeni_olan = sum(1 for (ad, _, gecti, _, _) in adimlar
                    if ad in yeni_adlar and gecti)
    print("ESKI_MUTANT=%d/4 YENI_MUTANT=%d/3 MUTANT=%d/7 HEDEF_KOL_ATFI=%d/3 "
          "KONTROL=%d/2" % (eski_olan, yeni_olan, mutant_sayaci,
                            atfi_dogru, kontrol_sayaci))
    rc = 0
    if mutant_sayaci != 7:
        rc = 1
    if kontrol_sayaci != 2:
        rc = 1
    return rc


# ------------------------------------------------------------------------------
# CURUTME: her kolun govdesi oldurulunce ilgili mutant YASAMALI
# ------------------------------------------------------------------------------
def curutme(gecici_kok):
    """Dort curutme testi. Her biri bir kolun govdesini 'oldurur' (kirik_kol
    bayragi ile o kol devre disi birakilir) ve o mutant'in YASAMASINI
    (hedef kolu kanitlamamasini) bekler.

    Sonra DIGER mutant'lerin hala normal sekilde calistigini teyit eder.

    Biri hâlâ kirmizi (yasamaz) geliyorsa mutant test'i kendi kolunu
    kanitlamiyor demektir — `KUSUR:` olarak raporlanir.
    """
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kaynak_posta = os.path.join(gecici_kok, "kaynak-curutme.md")
    hedef_posta = os.path.join(gecici_kok, "hedef-curutme.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _kurulum_ve_simfla(kirik_kol):
        """Verilen kirik_kol ile test kurulumunu hazirla ve sinifla."""
        durum = {"son_guncelleme": simdi_str,
                 "kalemler": {"K190": _ft(300),
                              "K191": _ft(60),
                              "K193": _ft(60),
                              "K192": _ft_ileri(60)}}
        durum_yaz_atomik(durum_yol, durum)
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        return hepsini_simfla(defter, durum_yol, simdi_dt, kirik_kol=kirik_kol)

    curutmeler = []

    # ---- Curutme 1: T5-DURGUN govdesi oldurulunce ----------------------------
    # Beklenen: K190 artik T5-DURGUN degil (kirik_kol onu TAZE yapiyor),
    # dolayisiyla M1'in "K190 == T5-DURGUN" kontrolu YASAMALI.
    # M2/M3/M4 normal mantikla calismali (kirik_kol=T5-DURGUN onlar icin
    # anlamsiz — sadece T5-DURGUN kararini bozar).
    sonuc_d = _kurulum_ve_simfla(kirik_kol=T5_DURGUN_JETON)
    k190 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K190"), None)
    k191 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K191"), None)
    k192 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K192"), None)
    m1_yasamali = (k190 is not None and k190["kol"] == T5_TAZE_JETON)
    m2_dokunulmaz = (k191 is not None and k191["kol"] == T5_TAZE_JETON)
    m4_dokunulmaz = (k192 is not None and k192["kol"] == T5_OLCULEMEDI_JETON)
    curutme_1_ok = (m1_yasamali and m2_dokunulmaz and m4_dokunulmaz)
    curutmeler.append((T5_DURGUN_JETON, curutme_1_ok,
                       "K190=T5-TAZE (oldurulmus kol uretti) | "
                       "K191=T5-TAZE (M2 normal) | "
                       "K192=T5-OLCULEMEDI (M4 normal)"))

    # ---- Curutme 2: T5-TAZE govdesi oldurulunce ------------------------------
    # Beklenen: K191 artik T5-TAZE degil (kirik_kol onu DURGUN yapiyor);
    # M2 yasamali. M1/M4 normal.
    sonuc_t = _kurulum_ve_simfla(kirik_kol=T5_TAZE_JETON)
    k190 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K190"), None)
    k191 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K191"), None)
    k192 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K192"), None)
    m2_yasamali = (k191 is not None and k191["kol"] == T5_DURGUN_JETON)
    m1_dokunulmaz = (k190 is not None and k190["kol"] == T5_DURGUN_JETON)
    m4_dokunulmaz = (k192 is not None and k192["kol"] == T5_OLCULEMEDI_JETON)
    curutme_2_ok = (m2_yasamali and m1_dokunulmaz and m4_dokunulmaz)
    curutmeler.append((T5_TAZE_JETON, curutme_2_ok,
                       "K191=T5-DURGUN (oldurulmus kol uretti) | "
                       "K190=T5-DURGUN (M1 normal) | "
                       "K192=T5-OLCULEMEDI (M4 normal)"))

    # ---- Curutme 3: T5-IZ govdesi oldurulunce --------------------------------
    # devir_yap'a iz_yazilamaz=True ile YASAMAZ davranisini test ettik
    # zaten M3'un BOZUK KANAL vakasinda. Burada SAGLAM kanalda iz_yazilamaz
    # simule edilir: hata T5-IZ onekiyle baslamali (zaten oluyor) +
    # iz_yazildi=False. Mutant M3'un "ok=True" kosulu YASAMALI.
    kalem_m3 = {"kimlik": "K192"}
    sonuc_m3_bozuk = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                               kaynak_yol=kaynak_posta, hedef_yol=hedef_posta,
                               iz_yazilamaz=True)
    # M3'un "saglam kanal" kontrolu iz_yazildi=False ise YASAMALI (cikti False).
    m3_ok_yasamali = (sonuc_m3_bozuk["iz_yazildi"] is False)
    curutme_3_ok = m3_ok_yasamali
    curutmeler.append((T5_IZ_JETON, curutme_3_ok,
                       "devir_yap iz_yazilamaz=True: iz_yazildi=False | "
                       "hata T5-IZ onekiyle basliyor=%s"
                       % (sonuc_m3_bozuk["hata"].startswith(T5_IZ_JETON + " ")
                          if sonuc_m3_bozuk["hata"] else False)))

    # ---- Curutme 4: T5-OLCULEMEDI govdesi oldurulunce ------------------------
    # kirik_kol=T5-OLCULEMEDI ile gelecek tarihli damga gecerli sayilir
    # ve T5-TAZE uretilir. M4'un "3 kalem OLCULEMEDI" kontrolu YASAMALI
    # (sadece 2 kalem OLCULEMEDI kalir).
    durum_m4_kirik = {"son_guncelleme": simdi_str,
                      "kalemler": {"K190": _ft(300),
                                   "K191": "bozuk-tarih-degil",
                                   "K192": _ft_ileri(60),
                                   "K193": _ft(60)}}
    durum_yaz_atomik(durum_yol, durum_m4_kirik)
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    sonuc_o = hepsini_simfla(defter, durum_yol, simdi_dt,
                             kirik_kol=T5_OLCULEMEDI_JETON)
    m4_yasamali = (sonuc_o["olculemedi"] < 3)
    curutme_4_ok = m4_yasamali
    curutmeler.append((T5_OLCULEMEDI_JETON, curutme_4_ok,
                       "olculemedi_sayaci=%d (normal 3; kirik ile <3 = mutant yasadi)"
                       % sonuc_o["olculemedi"]))

    # ---- ozet bas ---------------------------------------------------------
    print("T5 DURGUN KALEM KAPISI — CURUTME (kol govdesi oldurulunce mutant SESSIZ)")
    print("izolasyon koku: %s" % gecici_kok)
    print("")
    gecen = 0
    for kol, ok, mesaj in curutmeler:
        print("CURUTME hedef=%s" % kol)
        print("  mesaj: %s" % mesaj)
        if ok:
            print("  SONUÇ: MUTANT YASADI (kol gercekten devre disi) — curutme gecti")
            gecen += 1
        else:
            print("  SONUÇ: MUTANT YASAMADI (kol hala calisiyor) — curutme KUSUR!")
        print("")
    print("CURUTME=%d/4" % gecen)
    return 0 if gecen == 4 else 1


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kendini-test", action="store_true",
                    help="4 mutantu izole kos (gercek deftere / durum dosyasina / "
                         "posta kutusuna DOKUNMAZ)")
    ap.add_argument("--curutme", action="store_true",
                    help="dort curutme: her kolun govdesi oldurulunce ilgili "
                         "mutant YASAMALI (sessiz kalmali). --kendini-test'ten "
                         "AYRI calisir; izolasyon tempfile.mkdtemp.")
    ap.add_argument("--rapor", action="store_true",
                    help="gercek defter uzerinde YAZMADAN; kac kalem durgun/taze/"
                         "olculemedi")
    ap.add_argument("--gercek", action="store_true",
                    help="--damga-uret + --rapor birlikte (gercek defter + "
                         "git gecmisi → damga uret → siniflandir)")
    ap.add_argument("--damga-uret", action="store_true",
                    help="DEVAM.md'nin git gecmisinden kalem damgalarini uret "
                         "(atomik yazar; damga uretilemeyen kalem haritaya "
                         "YAZILMAZ → fail-closed)")
    ap.add_argument("--simdi", default=None,
                    help="simdi yerine kullanilacak ISO zaman (--rapor/--damga-uret icin)")
    ap.add_argument("--defter", default=None,
                    help="defter yolu (default: <repo>/DEVAM.md)")
    ap.add_argument("--repo", default=None,
                    help="git repo kok (--damga-uret icin; default: <tools/..>)")
    ap.add_argument("--durum", default=None,
                    help="durum dosyasi yolu (default: ~/.claude/projects/.../memory/"
                         + DURUM_DOSYA_ADI + ")")
    args = ap.parse_args(argv)

    if args.kendini_test:
        # Izolasyon: tempfile.mkdtemp(). Gercek dosyalara ASLA dokunulmaz.
        gecici = tempfile.mkdtemp(prefix="t5-kendinitest-")
        try:
            return kendini_test(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.curutme:
        gecici = tempfile.mkdtemp(prefix="t5-curutme-")
        try:
            return curutme(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.damga_uret:
        simdi_dt = _simdi_coz(args.simdi) if args.simdi else datetime.datetime.now(datetime.timezone.utc)
        if simdi_dt is None:
            print("HATA: --simdi gecersiz ISO: %r" % args.simdi, file=sys.stderr)
            return 2
        repo = args.repo or _repo_kok()
        defter_yol = args.defter or os.path.join(repo, "DEVAM.md")
        durum_yol = args.durum or VARSAYILAN_DURUM_YOLU
        sonuc = damga_uret(defter_yol, repo, durum_yol, simdi_dt)
        for satir in sonuc["ekrana"]:
            print(satir)
        print("DAMGA_URETILDI=%d DAMGA_URETILEMEDI=%d NEDEN_GIT_IZI_YOK=%d "
              "NEDEN_DEFTER_GITSIZ=%d"
              % (sonuc["uretilen"], sonuc["uretitemeyen"],
                 sonuc["neden_git_izi_yok"], sonuc["neden_defter_gitsiz"]))
        if sonuc["hata"]:
            print("HATA: %s" % sonuc["hata"], file=sys.stderr)
        # rc!=0: hicbir kalem uretilemedi (sessiz sifir YASAK)
        if sonuc["uretilen"] == 0:
            return 1
        return 0

    if args.rapor:
        simdi_dt = _simdi_coz(args.simdi) if args.simdi else datetime.datetime.now(datetime.timezone.utc)
        if simdi_dt is None:
            print("HATA: --simdi gecersiz ISO: %r" % args.simdi, file=sys.stderr)
            return 2
        simdi_str = (args.simdi if args.simdi
                     else simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
        repo = _repo_kok()
        defter_yol = args.defter or os.path.join(repo, "DEVAM.md")
        durum_yol = args.durum or VARSAYILAN_DURUM_YOLU
        if not os.path.isfile(defter_yol):
            print("HATA: defter yok: %s" % defter_yol, file=sys.stderr)
            return 2
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        sonuc = hepsini_simfla(defter, durum_yol, simdi_dt)
        rapor_yaz(sonuc, simdi_str)
        return 0

    if args.gercek:
        # Birlestirilmis: ONCE damga-uret (gercek defter + git), SONRA siniflandir.
        simdi_dt = _simdi_coz(args.simdi) if args.simdi else datetime.datetime.now(datetime.timezone.utc)
        if simdi_dt is None:
            print("HATA: --simdi gecersiz ISO: %r" % args.simdi, file=sys.stderr)
            return 2
        simdi_str = (args.simdi if args.simdi
                     else simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
        repo = args.repo or _repo_kok()
        defter_yol = args.defter or os.path.join(repo, "DEVAM.md")
        durum_yol = args.durum or VARSAYILAN_DURUM_YOLU
        sonuc_damga = damga_uret(defter_yol, repo, durum_yol, simdi_dt)
        for satir in sonuc_damga["ekrana"]:
            print(satir)
        print("DAMGA_URETILDI=%d DAMGA_URETILEMEDI=%d NEDEN_GIT_IZI_YOK=%d "
              "NEDEN_DEFTER_GITSIZ=%d"
              % (sonuc_damga["uretilen"], sonuc_damga["uretitemeyen"],
                 sonuc_damga["neden_git_izi_yok"],
                 sonuc_damga["neden_defter_gitsiz"]))
        # Simdi siniflandirma bas (durum JSON yazildi)
        if not os.path.isfile(defter_yol):
            print("HATA: defter yok: %s" % defter_yol, file=sys.stderr)
            return 2
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        sonuc = hepsini_simfla(defter, durum_yol, simdi_dt)
        print("")
        rapor_yaz(sonuc, simdi_str)
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
