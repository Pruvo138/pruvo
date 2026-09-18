#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K309 MENZIL KAPISI — "defterin gormedigi kalem id'si" sayisini OLCER.

🔴 OLCULEN SINIF (K309, 26 Agu 2026; 13 Eyl'de mimar sayimiyla tekrarlandi):
acik-kalemler.md defteri nobetin ve parti kapisinin ölçüm EVRENIDIR — o defterde
satiri OLMAYAN bir kalem ne kapanabilir ne olculebilir. Ama `DEVAM.md` ve
`DEVAM-ARSIV.md`'de K<n> id'siyle yasayan kalemlerin buyuk kismi defterde satir
ACMAMIS: 13 Eyl mimar sayimi K110–K270 araliginda defterde 6 satir, kayitlarda
148 id buldu -> MENZIL_DISI 142. Yani kapi VAR, kural VAR, MENZIL kuyrugun
yarisini GORMUYOR ([[kapinin-menzili-cagri-yeridir]]).

BU KAPI NE YAPAR: kayit duzlemlerinde (DEVAM.md ∪ DEVAM-ARSIV.md) gecen K<n>
id'lerinden defterde SATIRI OLMAYANLARIN sayisini basar, olculmus TABAN ile
kiyaslar ve YALNIZ ARTISTA kirmizi yanar.

🔴 NE YAPMAZ — ve nicin: bugunku ~140'i kirmiziya cevirmez. Tabani "0" diye
civilemek kataloğu ANINDA yakardi ve kapi ilk kosumda kapatilirdi
([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]). Taban ELLE YAZILMAZ,
`--taban-yaz` ile OLCULEREK yazilir ([[olcut-civilenirken-taban-olculmeli]]).

🔴 FAIL-CLOSED: bu kayit duzlemleri repo/ev DISINDA da olabilir (DEVAM-ARSIV.md
git disidir, CI'da YOKTUR). Dosya bulunamazsa kapi SESSIZ YESIL DONMEZ:
`OLCULEMEDI` + sifir-disi rc basar ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
Muafiyet listesi kabul DEGILDIR.

🔴 IKINCI PARSER YOK: defter satirlari `parti-borc-kapisi.py::kalem_kimlikleri`
(o da `hucrelere_bol`/`TabloSatir`/`_ayrac_satiri_mi` ilkellerini kullanir)
uzerinden okunur. Burada markdown tablosu ELLE bolunmez.

CIKIS KODLARI
  0  TABAN_ALTINDA / TABAN_ESIT — menzil disi sayisi tabani ASMIYOR
  3  ARTIS — menzil disi sayisi tabani ASTI (kirmizi)
  4  OLCULEMEDI — kaynak/defter okunamadi, taban cozulemedi

KOSUM
  python3 tools/kalem-menzil-kapisi.py                  # gercek duzlemler
  python3 tools/kalem-menzil-kapisi.py --taban-yaz      # tabani OLCEREK civile
  python3 tools/kalem-menzil-kapisi.py --menzil-listesi /yol/K309-MENZIL.md
  python3 tools/kalem-menzil-kapisi.py --kendini-test   # fiksturlu batarya
"""

import argparse
import importlib.util
import json
import os
import re
import sys

ARAC_KOK = os.path.dirname(os.path.abspath(__file__))
REPO_KOK = os.path.dirname(ARAC_KOK)

# --- TEK PARSER: parti-borc-kapisi.py ---------------------------------------
# Dosya adinda tire var -> normal `import` calismaz; spec ile yuklenir.
_PBK_YOL = os.path.join(ARAC_KOK, "parti-borc-kapisi.py")


def _pbk_yukle(yol=None):
    yol = yol or _PBK_YOL
    spec = importlib.util.spec_from_file_location("_k309_pbk", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- KIMLIK DESENI ----------------------------------------------------------
# `K` + 2..4 rakam, ILK RAKAM SIFIR DEGIL. Onunde harf/rakam OLMAZ (`OK309`,
# `2K3` eslesmez), ardinda rakam OLMAZ. Sonek (`-31AGU`, `-EK`) TABANA
# indirgenir: defterde `K351` satiri varken `K351-31AGU` ayri bir menzil kalemi
# SAYILMAZ. Menzil ekseni "bu kalem ailesinin defterde bir satiri var mi".
#
# 🔴 NICIN TEK HANE DISARIDA — DARALTMA DEGIL, YANLIS ALAN ELEMESI (olculdu
# 16 Eyl 2026): `K0`/`K1`/`K2` kayitlarda KALEM ID'SI DEGIL, MUTANT/EKSEN
# ETIKETIDIR ("K1 mutantindan TURER", "K0 ORNEKLEM ekseni", "(K1-K7,",
# "{K1,X1}"). Defterin EN KUCUK gercek id'si `K20` (olculdu: defter id'leri
# 20,21,22,... ile basliyor). Tek haneli eslesmeler menzil sayisini SAHTE
# olarak sisirir ve kapinin sinyalini bogar
# ([[eslesme-anahtari-yanlissa-sifir-bulgu-yesil-sanilir]]). Bastaki sifir da
# elenir: `K001`/`K02` kalem id'si degildir.
KIMLIK_RE = re.compile(r"(?<![A-Za-z0-9])K([1-9]\d{1,3})(?![0-9])")

# Arsivde son gorunen DURUM JETONU (K309-MENZIL.md dokumu icin).
JETON_KAPALI = re.compile(r"KAPANDI|KAPANDİ|KAPANMIŞ|KAPANMIS|KAPATILDI|✅")
JETON_ACIK = re.compile(r"\bACIK\b|\bAÇIK\b|UCUSTA|UÇUŞTA|BEKLETMEDE|🔴")

VARSAYILAN_KAYNAKLAR = (
    os.path.join(REPO_KOK, "DEVAM.md"),
    os.path.join(REPO_KOK, "DEVAM-ARSIV.md"),
)
VARSAYILAN_DEFTER = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md")
TABAN_DOSYA = os.path.join(ARAC_KOK, "k309-menzil-taban.json")


def kimlik_tabani(ham):
    """`K351-31AGU` -> `K351`; `K309` -> `K309`. Eslesmezse None."""
    m = KIMLIK_RE.search(ham or "")
    return "K%s" % m.group(1) if m else None


# M5 mutanti icin: rakam tabani/bastaki-sifir kolu KALDIRILMIS desen.
_M5_KIMLIK_RE = re.compile(r"(?<![A-Za-z0-9])K(\d{1,4})(?![0-9])")


def _desen(mutant):
    return _M5_KIMLIK_RE if mutant == "M5" else KIMLIK_RE


def kaynak_kimlikleri(yollar, *, mutant=None):
    """Kayit duzlemlerinde gecen K<n> id'leri -> {id: [(yol, satir_no, satir)]}

    Fail-closed: yollardan HERHANGI BIRI yoksa (set(), False, sebep).
    """
    if mutant == "M3":
        # KOL OLU: eksik dosya SESSIZCE atlanir -> menzil kucuk gorunur, rc=0.
        yollar = [y for y in yollar if os.path.isfile(y)]
    eksik = [y for y in yollar if not os.path.isfile(y)]
    if eksik:
        return {}, False, "kayit duzlemi YOK: %s" % ", ".join(eksik)
    gecisler = {}
    for yol in yollar:
        try:
            with open(yol, encoding="utf-8", errors="replace") as f:
                for satir_no, satir in enumerate(f, start=1):
                    for m in _desen(mutant).finditer(satir):
                        kid = "K%s" % m.group(1)
                        gecisler.setdefault(kid, []).append(
                            (yol, satir_no, satir.rstrip("\n")))
        except OSError as e:
            return {}, False, "kayit duzlemi okunamadi (IO) %s: %r" % (yol, e)
    return gecisler, True, None


def defter_kimlikleri(defter_yolu, *, pbk=None, mutant=None):
    """Defterde satiri olan TUM kimlikler (durum bagimsiz) -> taban id kumesi."""
    pbk = pbk or _pbk_yukle()
    if mutant == "M4":
        # KOL BOZUK: yalniz ACIK satirlar sayilir. Kapanmis kalemin satiri
        # GORUNMEZ olur -> menzil disi sayisi SISER (K309'un asil tuzagi).
        kalemler, ok, hata = pbk.acik_kalem_listesi(defter_yolu)
        ham = [k["kimlik"] for k in kalemler] if ok else []
    else:
        kumeler, ok, hata = pbk.kalem_kimlikleri(defter_yolu)
        ham = list(kumeler) if ok else []
    if not ok:
        return set(), False, hata
    tabanlar = set()
    for h in ham:
        t = kimlik_tabani(h)
        if t:
            tabanlar.add(t)
    return tabanlar, True, None


def son_durum_jetonu(gecis_satirlari):
    """Id'nin kayitlardaki SON gecisinden durum jetonu cikar.

    KAPANDI | ACIK | belirsiz. Ayni satirda ikisi de gecerse `belirsiz`
    ([[hal-jeton-onceligini-ortak-satir-kapatir]] sinifi: ortak satir jeton
    onceligini KAPATIR — burada uydurmak yerine BELIRSIZ deriz).
    """
    if not gecis_satirlari:
        return "belirsiz"
    _yol, _no, satir = gecis_satirlari[-1]
    kapali = bool(JETON_KAPALI.search(satir))
    acik = bool(JETON_ACIK.search(satir))
    if kapali and not acik:
        return "KAPANDI"
    if acik and not kapali:
        return "ACIK"
    return "belirsiz"


def taban_oku(yol=TABAN_DOSYA, *, mutant=None):
    """(taban_int, ok, hata). Dosya yoksa/bozuksa FAIL-CLOSED."""
    if mutant == "M2":
        # KOL OLU: taban cozulemese de 10**9 varsayilir -> hicbir artis kirmizi
        # yanmaz; kapi ADI VAR, HUKMU YOK.
        return 10 ** 9, True, None
    if not os.path.isfile(yol):
        return None, False, "taban dosyasi YOK: %s (once --taban-yaz)" % yol
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        return None, False, "taban okunamadi: %r" % e
    if not isinstance(veri.get("menzil_disi"), int):
        return None, False, "taban dosyasinda `menzil_disi` tamsayisi YOK"
    return veri["menzil_disi"], True, None


def taban_yaz(sayi, yol=TABAN_DOSYA, *, kaynaklar=(), defter=""):
    """🔴 TABAN ELLE YAZILMAZ — bu fonksiyon YALNIZ olculmus sayiyi kabul eder."""
    veri = {
        "menzil_disi": int(sayi),
        "olcum_komutu": "python3 tools/kalem-menzil-kapisi.py --taban-yaz",
        "kaynaklar": [os.path.basename(k) for k in kaynaklar],
        "defter": os.path.basename(defter),
        "not": ("K309 menzil tabani. ELLE DEGISTIRILMEZ; yalniz --taban-yaz "
                "ile OLCULEREK guncellenir. Sayi DUSTUKCE tekrar civilenir."),
    }
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return veri


def olc(kaynaklar, defter, *, pbk=None, mutant=None):
    """Return dict: MENZIL_DISI sayisi + dokum. Fail-closed alanlari tasir."""
    gecisler, kok, k_hata = kaynak_kimlikleri(list(kaynaklar), mutant=mutant)
    if not kok:
        return {"OK": False, "SEBEP": k_hata}
    defter_ids, dok, d_hata = defter_kimlikleri(defter, pbk=pbk, mutant=mutant)
    if not dok:
        return {"OK": False, "SEBEP": d_hata}
    if mutant == "M1":
        # KOL OLU: fark HIC hesaplanmaz, menzil daima BOS -> kapi ADI VAR,
        # OLCUMU YOK (K309'un tarif ettigi sahte yesilin ta kendisi).
        menzil = []
    else:
        menzil = sorted((k for k in gecisler if k not in defter_ids),
                        key=lambda k: int(k[1:]))
    return {
        "OK": True,
        "KAYNAK_ID": len(gecisler),
        "DEFTER_ID": len(defter_ids),
        "MENZIL_DISI": len(menzil),
        "MENZIL": menzil,
        "GECISLER": gecisler,
    }


def menzil_listesi_yaz(yol, sonuc, kaynaklar, defter):
    satirlar = [
        "# K309 — MENZIL DISI KALEM ID'LERI",
        "",
        "Kayit duzlemlerinde (`%s`) gecen ama defterde (`%s`) SATIRI OLMAYAN"
        % (", ".join(os.path.basename(k) for k in kaynaklar),
           os.path.basename(defter)),
        "kalem id'leri. Uretici: `python3 tools/kalem-menzil-kapisi.py"
        " --menzil-listesi <yol>` — ELLE DUZENLENMEZ.",
        "",
        "KAYNAK_ID=%d DEFTER_ID=%d MENZIL_DISI=%d"
        % (sonuc["KAYNAK_ID"], sonuc["DEFTER_ID"], sonuc["MENZIL_DISI"]),
        "",
        "| id | son gorulen durum jetonu | gecis sayisi |",
        "|---|---|---|",
    ]
    sayim = {"KAPANDI": 0, "ACIK": 0, "belirsiz": 0}
    for kid in sonuc["MENZIL"]:
        gecis = sonuc["GECISLER"][kid]
        jeton = son_durum_jetonu(gecis)
        sayim[jeton] += 1
        satirlar.append("| %s | %s | %d |" % (kid, jeton, len(gecis)))
    satirlar.append("")
    satirlar.append("KIRILIM: KAPANDI=%d ACIK=%d belirsiz=%d"
                    % (sayim["KAPANDI"], sayim["ACIK"], sayim["belirsiz"]))
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    return sayim


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kaynak", action="append", default=None,
                   help="kayit duzlemi (tekrarlanabilir). Varsayilan:"
                        " DEVAM.md + DEVAM-ARSIV.md")
    p.add_argument("--defter", default=VARSAYILAN_DEFTER,
                   help="acik-kalemler.md yolu")
    p.add_argument("--taban-dosya", default=TABAN_DOSYA)
    p.add_argument("--taban-yaz", action="store_true",
                   help="tabani OLCEREK yaz (elle sayi YAZILMAZ)")
    p.add_argument("--menzil-listesi", default=None,
                   help="menzil disi id dokumunu bu dosyaya yaz")
    p.add_argument("--kendini-test", action="store_true")
    a = p.parse_args(argv)

    if a.kendini_test:
        return kendini_test()

    kaynaklar = a.kaynak or list(VARSAYILAN_KAYNAKLAR)
    sonuc = olc(kaynaklar, a.defter)
    if not sonuc["OK"]:
        print("OLCULEMEDI: %s" % sonuc["SEBEP"])
        print("HUKUM=OLCULEMEDI rc=4")
        return 4

    print("KAYNAKLAR=%s" % ",".join(os.path.basename(k) for k in kaynaklar))
    print("DEFTER=%s" % a.defter)
    print("KAYNAK_ID=%d DEFTER_ID=%d MENZIL_DISI=%d  [KAPI]"
          % (sonuc["KAYNAK_ID"], sonuc["DEFTER_ID"], sonuc["MENZIL_DISI"]))

    if a.menzil_listesi:
        sayim = menzil_listesi_yaz(a.menzil_listesi, sonuc, kaynaklar, a.defter)
        print("MENZIL_LISTESI=%s KAPANDI=%d ACIK=%d belirsiz=%d"
              % (a.menzil_listesi, sayim["KAPANDI"], sayim["ACIK"],
                 sayim["belirsiz"]))

    if a.taban_yaz:
        veri = taban_yaz(sonuc["MENZIL_DISI"], a.taban_dosya,
                         kaynaklar=kaynaklar, defter=a.defter)
        print("TABAN_YAZILDI=%d dosya=%s" % (veri["menzil_disi"], a.taban_dosya))
        return 0

    taban, tok, t_hata = taban_oku(a.taban_dosya)
    if not tok:
        print("OLCULEMEDI: %s" % t_hata)
        print("HUKUM=OLCULEMEDI rc=4")
        return 4
    print("TABAN=%d" % taban)
    if sonuc["MENZIL_DISI"] > taban:
        print("HUKUM=ARTIS rc=3 menzil_disi=%d > taban=%d — defter EVRENININ"
              " disinda kalan kalem SAYISI BUYUDU; yeni id'ler defterde satir"
              " ACMALI (ya da taban ölçülerek DUSURULMELI)"
              % (sonuc["MENZIL_DISI"], taban))
        return 3
    if sonuc["MENZIL_DISI"] < taban:
        print("HUKUM=TABAN_ALTINDA rc=0 menzil_disi=%d < taban=%d — taban"
              " `--taban-yaz` ile DUSURULEBILIR" % (sonuc["MENZIL_DISI"], taban))
        return 0
    print("HUKUM=TABAN_ESIT rc=0 menzil_disi=%d" % sonuc["MENZIL_DISI"])
    return 0


# ---------------------------------------------------------------------------
# KENDINI TEST — fiksturler tempfile altinda; GERCEK defter/kayit OKUNMAZ.
# ---------------------------------------------------------------------------
_GECEN = []
_KALAN = []


def _iddia(ad, kosul, kanit=""):
    if kosul:
        _GECEN.append(ad)
        print("  ✅ %s" % ad)
    else:
        _KALAN.append(ad)
        print("  ❌ %s\n     kanit: %s" % (ad, str(kanit)[:400]))


_DEFTER_FIKSTUR = """# ACIK KALEMLER

| kimlik | tarih | kim | is | durum | kapanis kaniti |
|---|---|---|---|---|---|
| K100 | 2026-08-01 | A→B | is metni kabul: python3 x.py | ACIK | — |
| K101 | 2026-08-02 | A→B | is metni kabul: python3 y.py | KAPANDI | sha |
| K351-31AGU | 2026-08-31 | A→B | is metni kabul: python3 z.py | ACIK | — |
"""

_DEVAM_FIKSTUR = """# DEVAM
K100 uzerinde calisildi.
K102 acik gorunuyor 🔴 ACIK
"""

_ARSIV_FIKSTUR = """# ARSIV
K101 KAPANDI diye gecti.
K103 KAPANDI ✅ olarak kapandi.
K104 hakkinda hicbir jeton yok, duz metin.
K351 ailesi UCUSTA.
OK309 ve 2K3 ESLESMEZ; K1050 dort haneli, ESLESIR.
🔴 GURULTU SATIRI: K1 mutantindan TURER, K0 ORNEKLEM ekseni, K001 ve K02 de
kalem id'si DEGILDIR — hicbiri menzile GIRMEMELI.
"""


def _fikstur_kur(kok, *, defter=_DEFTER_FIKSTUR, devam=_DEVAM_FIKSTUR,
                 arsiv=_ARSIV_FIKSTUR):
    d = os.path.join(kok, "acik-kalemler.md")
    v = os.path.join(kok, "DEVAM.md")
    r = os.path.join(kok, "DEVAM-ARSIV.md")
    for yol, icerik in ((d, defter), (v, devam), (r, arsiv)):
        if icerik is not None:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(icerik)
    return d, v, r


def kendini_test():
    import shutil
    import tempfile
    kok = tempfile.mkdtemp(prefix="k309-menzil-")
    try:
        pbk = _pbk_yukle()
        defter, devam, arsiv = _fikstur_kur(kok)
        kaynaklar = [devam, arsiv]

        print("\n[1] KIMLIK DESENI — sonek TABANA iner, komsu sekiller ESLESMEZ")
        _iddia("1a `K351-31AGU` -> K351", kimlik_tabani("K351-31AGU") == "K351",
               kimlik_tabani("K351-31AGU"))
        _iddia("1b `K309` -> K309", kimlik_tabani("K309") == "K309")
        _iddia("1c `OK309` ESLESMEZ (onunde harf)",
               KIMLIK_RE.search("OK309") is None)
        _iddia("1d `2K3` ESLESMEZ (onunde rakam)",
               KIMLIK_RE.search("2K3") is None)
        _iddia("1e `K1050` ESLESIR (4 hane)",
               kimlik_tabani("K1050") == "K1050")
        _iddia("1f 🔴 `K1` ESLESMEZ (tek hane = mutant/eksen etiketi)",
               KIMLIK_RE.search("K1 mutantindan TURER") is None)
        _iddia("1g 🔴 `K0` ESLESMEZ", KIMLIK_RE.search("K0 ORNEKLEM") is None)
        _iddia("1h 🔴 `K001` ESLESMEZ (bastaki sifir)",
               KIMLIK_RE.search(" K001 ") is None)
        _iddia("1i 🔴 `K02` ESLESMEZ (bastaki sifir)",
               KIMLIK_RE.search(" K02 ") is None)
        _iddia("1j KONTROL: `K20` (defterin en kucuk gercek id'si) ESLESIR",
               kimlik_tabani("K20") == "K20")

        print("\n[2] DEFTER PARSER — KAPANDI satiri da SATIRDIR (K309 tuzagi)")
        ids, ok, hata = defter_kimlikleri(defter, pbk=pbk)
        _iddia("2a defter okundu", ok, hata)
        _iddia("2b K100 (ACIK) defterde", "K100" in ids, sorted(ids))
        _iddia("2c 🔴 K101 (KAPANDI) da defterde — durum bagimsiz",
               "K101" in ids, sorted(ids))
        _iddia("2d K351-31AGU tabanina (K351) indi", "K351" in ids, sorted(ids))

        print("\n[3] MENZIL OLCUMU — gercek fark")
        s = olc(kaynaklar, defter, pbk=pbk)
        _iddia("3a olcum OK", s["OK"], s)
        _iddia("3b MENZIL_DISI=4 (K102 · K103 · K104 · K1050)",
               s["MENZIL_DISI"] == 4, s["MENZIL"])
        _iddia("3c menzil listesi tam ve SAYISAL sirali",
               s["MENZIL"] == ["K102", "K103", "K104", "K1050"], s["MENZIL"])
        _iddia("3d 🔴 K101 menzil DISI DEGIL (kapanmis ama SATIRI VAR)",
               "K101" not in s["MENZIL"], s["MENZIL"])
        _iddia("3e 🔴 K351 menzil DISI DEGIL (sonekli satir tabani kapsar)",
               "K351" not in s["MENZIL"], s["MENZIL"])

        print("\n[4] DURUM JETONU — KAPANDI / ACIK / belirsiz")
        _iddia("4a K103 -> KAPANDI",
               son_durum_jetonu(s["GECISLER"]["K103"]) == "KAPANDI",
               s["GECISLER"]["K103"])
        _iddia("4b K102 -> ACIK",
               son_durum_jetonu(s["GECISLER"]["K102"]) == "ACIK",
               s["GECISLER"]["K102"])
        _iddia("4c K104 -> belirsiz (jeton YOK, UYDURULMAZ)",
               son_durum_jetonu(s["GECISLER"]["K104"]) == "belirsiz",
               s["GECISLER"]["K104"])

        print("\n[5] TABAN — OLCULEREK yazilir, ARTISTA kirmizi")
        taban_yol = os.path.join(kok, "taban.json")
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", taban_yol, "--taban-yaz"])
        _iddia("5a --taban-yaz rc=0", rc == 0, rc)
        t, tok, _ = taban_oku(taban_yol)
        _iddia("5b taban OLCULEN sayidan yazildi (4)", tok and t == 4, t)
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", taban_yol])
        _iddia("5c taban ESIT -> rc=0", rc == 0, rc)

        # ARTIS: kayda YENI id gir.
        with open(arsiv, "a", encoding="utf-8") as f:
            f.write("K999 yepyeni bir kalem, defterde satiri YOK.\n")
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", taban_yol])
        _iddia("5d 🔴 ARTIS -> rc=3", rc == 3, rc)

        # DUSUS: defterde satir ac -> rc=0 (kapi is yapmayi ODULLENDIRIR).
        with open(defter, "a", encoding="utf-8") as f:
            f.write("| K999 | 2026-09-16 | A→B | is kabul: python3 q.py"
                    " | ACIK | — |\n")
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", taban_yol])
        _iddia("5e satir acilinca rc=0 (taban altinda)", rc == 0, rc)

        print("\n[6] FAIL-CLOSED — eksik duzlem SESSIZ YESIL DONMEZ")
        yok = os.path.join(kok, "OLMAYAN-ARSIV.md")
        rc = main(["--kaynak", devam, "--kaynak", yok, "--defter", defter,
                   "--taban-dosya", taban_yol])
        _iddia("6a eksik kaynak -> rc=4 OLCULEMEDI", rc == 4, rc)
        rc = main(["--kaynak", devam, "--kaynak", arsiv,
                   "--defter", os.path.join(kok, "OLMAYAN-DEFTER.md"),
                   "--taban-dosya", taban_yol])
        _iddia("6b defter yok -> rc=4 OLCULEMEDI", rc == 4, rc)
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", os.path.join(kok, "OLMAYAN-TABAN.json")])
        _iddia("6c taban dosyasi yok -> rc=4 OLCULEMEDI", rc == 4, rc)

        print("\n[7] MENZIL LISTESI — id + jeton + kirilim DISKE yazilir")
        liste = os.path.join(kok, "K309-MENZIL.md")
        rc = main(["--kaynak", devam, "--kaynak", arsiv, "--defter", defter,
                   "--taban-dosya", taban_yol, "--menzil-listesi", liste])
        metin = open(liste, encoding="utf-8").read()
        _iddia("7a liste yazildi", os.path.isfile(liste), liste)
        _iddia("7b K102 satiri ACIK jetonuyla", "| K102 | ACIK |" in metin,
               metin)
        _iddia("7c K104 satiri belirsiz", "| K104 | belirsiz |" in metin, metin)
        _iddia("7d KIRILIM satiri var", "KIRILIM: KAPANDI=" in metin, metin)

        print("\n[8] MUTANTLAR — her biri HEDEF KOLUNU adiyla oldurur")
        m1 = olc(kaynaklar, defter, pbk=pbk, mutant="M1")
        _iddia("8a 🔴 M1 (fark kolu olu) -> MENZIL_DISI 0'a duser, vaka 3b OLUR",
               m1["MENZIL_DISI"] == 0 and s["MENZIL_DISI"] != 0, m1)
        t2, tok2, _ = taban_oku(os.path.join(kok, "YOK.json"), mutant="M2")
        _iddia("8b 🔴 M2 (taban fail-closed olu) -> eksik taban YESIL olur,"
               " vaka 6c OLUR", tok2 and t2 == 10 ** 9, (tok2, t2))
        _, ok3, _ = kaynak_kimlikleri([devam, yok], mutant="M3")
        _iddia("8c 🔴 M3 (eksik duzlem atlanir) -> vaka 6a OLUR", ok3, ok3)
        m4 = olc(kaynaklar, defter, pbk=pbk, mutant="M4")
        _iddia("8d 🔴 M4 (yalniz ACIK satirlar sayilir) -> K101 menzil DISINA"
               " kayar, vaka 2c/3d OLUR", "K101" in m4["MENZIL"], m4["MENZIL"])
        m5 = olc(kaynaklar, defter, pbk=pbk, mutant="M5")
        _iddia("8e 🔴 M5 (rakam tabani kolu kalkti) -> `K1`/`K0` mutant"
               " etiketleri menzil kalemi SAYILIR, vaka 1f/1g OLUR",
               "K1" in m5["MENZIL"] and "K0" in m5["MENZIL"], m5["MENZIL"])
        print("\n[9] KONTROL — mesru durum YESIL kalir (mutant=None)")
        k = olc(kaynaklar, defter, pbk=pbk, mutant=None)
        _iddia("9a KONTROL: K101 hala menzil ICINDE", "K101" not in k["MENZIL"],
               k["MENZIL"])
        _iddia("9b KONTROL: K999 satiri acilinca menzil TABANA dondu (4)",
               k["MENZIL_DISI"] == 4, k["MENZIL"])
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("\nVAKA=%d DUSEN=%d" % (len(_GECEN) + len(_KALAN), len(_KALAN)))
    if _KALAN:
        print("HUKUM=KIRMIZI rc=1")
        return 1
    print("MUTANT=5/5 KONTROL=YESIL")
    print("HUKUM=YESIL rc=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
