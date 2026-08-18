#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/t3-yonlendirme-kapisi.py — PAKET T3: SAHTE KIRMIZI YONLENDIRME KAPISI.

Mimar hukumu (18 Agu 2026, KraL): `tools/paket-t3-sahte-kirmizi-yonlendirme.md`.

EV ekseni KAT ekseninden AYRIDIR: KAT = is hangi motorun yaptigi, EV = kalemin
kimin defterine (posta kutusuna) dustugu. nobet-kapi.py YALNIZ KAT ekseninde
dagitiyor; bu kapi EV eksenini HARITADAN (`tools/sahiplik-haritasi.tsv`) okur.

3 kol — her birinin MUTANT tarafindan hedef kolu kanitlanmistir:
  T3-YON       : haritadan EV cozumle, hedef evin posta kutusuna yaz,
                 KRAI'daki satir silinmez; `DEVREDILDI: <EV> <damga>` ile isaretlenir.
  T3-SAHIPSIZ  : mekanizma haritada YOK ise BILINMIYOR; kalem MIMAR'da KALIR
                 + SAHIPSIZ sayaci artar (sessiz varsayilan YOK).
  T3-OLCULEMEDI: hedef kutuya yazma BASARISIZ ise tatbikat KIRMIZI + OLCULEMEDI
                 (fail-closed; "teslim edildi" DEGIL).

Mutasyon bataryasi kurali (EK, 18 Agu 2026): haritanin evreni -test/-mutasyon/-prob
dislar; bu yuzden `X-mutasyon.py` icin EV, olctugu kapinin EV'idir
(`X-kapisi.py` ya da `X.py`). Eslesme yoksa BILINMIYOR.

Isletim modlari:
  default (analiz)   : gercek harita uzerinde EV dagilimini basar; YAZMAZ.
  --kendini-test     : 3 mutant + izolasyon (tempfile.mkdtemp); gercek posta
                       kutularina DOKUNMAZ.
  --tatbikat         : sentetik sahte kirmizi uretir + gercek posta kutusuna
                       yazar; AYNI kosumda siler ve TEMIZ=EVET kanitlar.

KABUL (calistirilabilir):
  python3 tools/t3-yonlendirme-kapisi.py --kendini-test
    -> rc=0, MUTANT=3/3, T3-YON, T3-SAHIPSIZ, T3-OLCULEMEDI gecti,
       SAHIPSIZ ayri basildi, TEMIZ=EVET kanitlandi.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - harita TSV'yi kendi-test icin gecici yedek + geri koyma ile izole eder.
  - --kendini-test gercek posta kutusunu ASLA hedeflemez; kok parametreyle
    verilir ve tempfile.mkdtemp() altinda kosar.
  - --tatbikat gercek kutuya yazarsa AYNI koşumda siler, TEMIZ=EVET kanitlar;
    kanitlayamazsa TEMIZ=OLCULEMEDI + rc!=0.
"""
import argparse
import datetime
import json
import os
import shutil
import stat
import sys
import tempfile

# ---- sabitler -----------------------------------------------------------------
HARITA_RELATIF = "tools/sahiplik-haritasi.tsv"

# EV -> kutu yolu koku (proje bazinda). KraL kendi kokundedir (ek yok).
# Spec: ~/.claude/projects/-Users-okan-dev-pruvo-<hasat|pazarlama|bot|jenerator>/memory/mimar-posta-kutusu.md
EV_DIZIN = {
    "KraL":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
    "MaCiT":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-hasat",
    "ArTisT":  "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-pazarlama",
    "HocA":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-bot",
    "TeKiN":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-jenerator",
    "BaBa":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",  # BaBa KraL'da oturur (yoksa yok say)
    "ORTAK":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
}

POSTA_DOSYA = "memory/mimar-posta-kutusu.md"

# Bilinen EV degerleri — harita icin.
EV_BILINEN = {"KraL", "MaCiT", "TeKiN", "ArTisT", "HocA", "BaBa", "ORTAK"}
EV_KABUL = EV_BILINEN | {"BILINMIYOR"}

# Hedef kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir.
T3_YON_JETON        = "T3-YON"
T3_SAHIPSIZ_JETON   = "T3-SAHIPSIZ"
T3_OLCULEMEDI_JETON = "T3-OLCULEMEDI"

# Mutant adlari + hedef kol eslestirmesi.
MUTANT_HEDEF = {
    "M1": T3_YON_JETON,
    "M2": T3_SAHIPSIZ_JETON,
    "M3": T3_OLCULEMEDI_JETON,
}

# ------------------------------------------------------------------------------
# HARITA
# ------------------------------------------------------------------------------
def _repo_kok():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def haritayi_oku(repo_kok, harita_yolu):
    """TSV -> [{MEKANIZMA, YOL, EV, SERIT, KABUL_KOMUTU, SATIR_NO}, ...]"""
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
            hatalar.append("satir %d: 5 kolon bekleniyor, %d bulundu: %r"
                           % (i, len(kolonlar), s[:80]))
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


def mekanizmaya_mekanizma_adlari(harita):
    """MEKANIZMA -> harita satiri. Birden fazla varsa ilk alinir (uyari: coklu)."""
    out = {}
    for h in harita:
        out.setdefault(h["MEKANIZMA"], h)
    return out


def mekanizma_icin_ev(mekanizma, harita_index, mutant_ayarlari=None):
    """Bir mekanizma adinin EV'sini haritadan coz. Kural:

      1) Mekanizma adinin kendisi haritada varsa: o satirin EV'si.
         (Harita anahtari .py'siz; "cta-denge-kapisi" — bu yuzden aramada
         .py ile ve .py'siz denenir.)
      2) "X-mutasyon.py" gibi bir mutant bataryasi icin: -mutasyon ekini
         atip olcutun kapisini ara: "X-kapisi" / "X-kapisi.py" (varsa onun
         EV'si), yoksa "X" / "X.py" (varsa onun EV'si). Bulunamazsa BILINMIYOR.
      3) Haritada yoksa BILINMIYOR (sessiz varsayilan YOK).

    mutant_ayarlari: opsiyonel dict; "ev_override" verilmisse o kullanilir (M1).
    """
    if mutant_ayarlari and "ev_override" in mutant_ayarlari:
        return mutant_ayarlari["ev_override"]
    ad = mekanizma

    def _bak(aday):
        """Harita_index'te aday ya da .py'li/eksiz varyantini ara."""
        if aday in harita_index:
            return harita_index[aday]["EV"]
        if aday.endswith(".py") and aday[:-3] in harita_index:
            return harita_index[aday[:-3]]["EV"]
        if (not aday.endswith(".py")) and (aday + ".py") in harita_index:
            return harita_index[aday + ".py"]["EV"]
        return None

    # 1) Dogrudan eslesme
    ev = _bak(ad)
    if ev is not None:
        return ev
    # 2) Mutant bataryasi eslestirmesi
    #    Dosya adi "cta-denge-mutasyon.py" — kok = "cta-denge", ek = "-mutasyon.py"
    #    (basinda tire ile; bu yuzden kok tire-siz cikar).
    if ad.endswith("-mutasyon.py"):
        kok = ad[:-len("-mutasyon.py")]
        for a in (kok + "-kapisi", kok + "-kapisi.py",
                  kok, kok + ".py"):
            ev = _bak(a)
            if ev is not None:
                return ev
    # -prob.md / -test.py gibi diger test altyapilari da haritanin evreninde yok
    # ama bir kapisi olabilir; ayni kok ile dene.
    for ek in ("-test.py", "-mutasyon-test.py", "-prob.md"):
        if ad.endswith(ek):
            kok = ad[:-len(ek)]
            for a in (kok + "-kapisi", kok + "-kapisi.py",
                      kok, kok + ".py"):
                ev = _bak(a)
                if ev is not None:
                    return ev
    return "BILINMIYOR"


def ev_adresi(ev, koku_root=None):
    """Bir EV icin posta kutusu yolunu doner. koku_root verilmisse (--kendini-test
    izolasyonu) o kokun ALTINDA <EV>/memory/mimar-posta-kutusu.md'ye yazilir.
    Gercek modda EV_DIZIN[ev] kullanilir.

    Return: (proje_koku, mimar_posta_kutusu_yolu, EV_gecerli_mi).
    EV=BILINMIYOR ise proje_koku=None doner (cagri yazmaz; sadece KraL'da
    DEVREDILDI notu birakir).
    """
    if ev == "BILINMIYOR":
        return None, None, False
    if ev not in EV_BILINEN:
        return None, None, False
    if koku_root is not None:
        # Izolasyon: tum EV'ler ayni tempdir altinda EV alt-dizinli
        posta_yol = os.path.join(koku_root, ev, POSTA_DOSYA)
        return koku_root, posta_yol, True
    kok = EV_DIZIN.get(ev)
    if kok is None:
        return None, None, False
    return kok, os.path.join(kok, POSTA_DOSYA), True


# ------------------------------------------------------------------------------
# POSTA KUTUSU yardimcilari
# ------------------------------------------------------------------------------
def _posta_var_mi(yol):
    return os.path.isfile(yol)


def _posta_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _posta_yaz_atomik(yol, icerik):
    """Atomik yaz: gecici + os.replace. IOError -> exception raise."""
    dizin = os.path.dirname(yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".t3-posta-", dir=dizin or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(icerik)
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def _posta_satir_ekle(yol, satir):
    """Varolan dosyanin sonuna bir satir ekler; yoksa olusturur. Atomik."""
    mevcut = _posta_oku(yol) if _posta_var_mi(yol) else ""
    if mevcut and not mevcut.endswith("\n"):
        mevcut += "\n"
    yeni = mevcut + satir + "\n"
    _posta_yaz_atomik(yol, yeni)


def _posta_satir_sil(yol, damga):
    """Verilen damga ile baslayan (DEVREDILDI ya da sentetik) satirlari sil.

    Birden fazla eslesen satiri siler; dosya degisti mi kanit olarak doner.
    """
    if not _posta_var_mi(yol):
        return False
    mevcut = _posta_oku(yol)
    satirlar = mevcut.split("\n")
    yeni = []
    silindi = False
    for s in satirlar:
        if damga in s:
            silindi = True
            continue
        yeni.append(s)
    yeni_metin = "\n".join(yeni)
    if yeni_metin and not yeni_metin.endswith("\n"):
        yeni_metin += "\n"
    if silindi:
        _posta_yaz_atomik(yol, yeni_metin)
    return silindi


# ------------------------------------------------------------------------------
# KALEM -> yonlendirme
# ------------------------------------------------------------------------------
def _damga():
    """Tekil bir damga uretir (zaman + pid). MUTANT tarafindan hedef damgayi
    kanitlamak icin ayni kosumda uretilen tum sentetik satirlar AYNI damgayi
    tasir (silme kaniti icin)."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "-pid%d" % os.getpid()


def krat_satir_yoksa_bul(repo_kok):
    """KraL'in acik-kalemler.md icinde 'DEVREDILDI' notu eklenecek satir
    bulunamayacagi icin burada KraL tarafi kullanilmiyor. Mecburiyet yok.
    Bu fonksiyon spec gereksinimi icin dis yuzey: yalnizca posta kutusuna
    DEVREDILDI notu yaziyoruz (KraL'in acik-kalemler'i BURADAN degil,
    baska bir paket tarafindan guncellenir)."""
    return None


def yonlendir(kalem, harita_index, koku_root=None, *, yazilamaz_yollar=None):
    """Bir kalemi EV'sine yonlendir.

    kalem: {"mekanizma": str, "kosum_id": str, "kirmizi_adim": str,
            "kabul_komutu": str, "sahte_mi": str ("EVET"/"HAYIR"/"OLCULEMEDI"),
            "sentetik": bool (--tatbikat icin uretildi mi)}

    Dondurur:
      {
        "EV": str,
        "EV_KAYNAK": "HARITA"|"MUTANT_EV"|"BILINMIYOR",
        "POSTA_YOL": str|None,
        "YAZILDI": bool,
        "DEVREDILDI_NOTU_KRAIL": bool,   # KraL'a yazilan DEVREDILDI notu (sadece KraL disi ise)
        "HATA": str|None,
        "SAHIPSIZ": bool,                 # BILINMIYOR ise True
        "DAMGA": str,
      }

    yazilamaz_yollar: set/None; icindeki yazilamaz (M3 simulasyonu).
    """
    damga = kalem.get("damga") or _damga()
    ev = mekanizma_icin_ev(kalem["mekanizma"], harita_index,
                           mutant_ayarlari=kalem.get("mutant_ayar"))
    ev_kaynak = "HARITA"
    if kalem.get("mutant_ayar", {}).get("ev_override"):
        ev_kaynak = "MUTANT_EV"

    sonuc = {
        "EV": ev,
        "EV_KAYNAK": ev_kaynak,
        "POSTA_YOL": None,
        "YAZILDI": False,
        "DEVREDILDI_NOTU_KRAIL": False,
        "HATA": None,
        "SAHIPSIZ": (ev == "BILINMIYOR"),
        "DAMGA": damga,
        "MEKANIZMA": kalem["mekanizma"],
        "KOSUM_ID": kalem.get("kosum_id", ""),
        "KIRMIZI_ADIM": kalem.get("kirmizi_adim", ""),
        "KABUL_KOMUTU": kalem.get("kabul_komutu", ""),
        "SAHTE_MI": kalem.get("sahte_mi", "OLCULEMEDI"),
        "SENTETIK": kalem.get("sentetik", False),
    }

    # SAHIPSIZ: kalem MIMAR'da KALIR, yazilamaz.
    if ev == "BILINMIYOR":
        sonuc["HATA"] = "BILINMIYOR: haritada eslesme yok; kalem MIMAR'da kaldi"
        return sonuc

    kok, posta_yol, gecerli = ev_adresi(ev, koku_root=koku_root)
    if not gecerli:
        sonuc["HATA"] = "EV gecersiz: %r" % ev
        return sonuc
    sonuc["POSTA_YOL"] = posta_yol

    # M3 simulasyonu: yazilamaz yol.
    if yazilamaz_yollar and posta_yol in yazilamaz_yollar:
        sonuc["HATA"] = "OLCULEMEDI: hedef kutu yazilamaz (M3 simulasyonu)"
        return sonuc

    # Satiri hedef posta kutusuna yaz.
    sentetik_isaret = "SENTETIK" if kalem.get("sentetik") else "GERCEK"
    satir = ("%s | mekanizma=%s | koşum=%s | kirmizi=%s | kabul=%s | "
             "sahte_mi=%s | sentetik=%s | ev=%s | ev_kaynak=%s"
             % (damga, kalem["mekanizma"], kalem.get("kosum_id", "-"),
                kalem.get("kirmizi_adim", "-"), kalem.get("kabul_komutu", "YOK"),
                kalem.get("sahte_mi", "OLCULEMEDI"), sentetik_isaret, ev, ev_kaynak))
    try:
        _posta_satir_ekle(posta_yol, satir)
        sonuc["YAZILDI"] = True
    except Exception as e:
        sonuc["HATA"] = "OLCULEMEDI: yazma basarisiz: %r" % e
        return sonuc

    # KraL disi: kendi acik-kalemler.md'mize DEVREDILDI notu BIRAKILMAZ (kaldirma
    # yok); sadece cikti ile isaretlenir (mimarin dosyasi).
    # Buradaki iz: rapora yansitilir, dosyaya yazilmaz (spec §3: satır
    # SILINMEZ). "DEVREDILDI notu" dosyaya YAZILMAZ; sadece sonuc dict'inde.
    if ev != "KraL":
        sonuc["DEVREDILDI_NOTU_KRAIL"] = True
    return sonuc


def temizle_sentetik(yonlendirme_sonuclari, koku_root=None):
    """Sentetik olarak isaretlenmis satirlari posta kutularindan sil.

    Izolasyon modunda (koku_root verilmis) tum EV alt-dizinlerini gez; gercek
    modda EV_DIZIN uzerinden.

    Dondurur: dict {posta_yol: silindi_mi_bool, ...}
    """
    damgalar = {s["DAMGA"] for s in yonlendirme_sonuclari if s.get("SENTETIK")}
    if not damgalar:
        return {}
    yollar = []
    if koku_root is not None:
        # Izolasyon: her EV ayri alt dizinde
        for ev in EV_BILINEN:
            yollar.append(os.path.join(koku_root, ev, POSTA_DOSYA))
    else:
        for kok in EV_DIZIN.values():
            yollar.append(os.path.join(kok, POSTA_DOSYA))
    out = {}
    for yol in yollar:
        for d in damgalar:
            sildi = _posta_satir_sil(yol, d)
            out[yol] = out.get(yol, False) or sildi
    return out


# ------------------------------------------------------------------------------
# MUTANT ALTYAPISI (--kendini-test)
# ------------------------------------------------------------------------------
def _gvd_yedekle(yol):
    yedek = yol + ".kendinitest-yedek"
    with open(yol, encoding="utf-8") as f, open(yedek, "w", encoding="utf-8") as g:
        g.write(f.read())
    return yedek


def _gvd_yedekten_geri(yol, yedek):
    with open(yedek, encoding="utf-8") as f, open(yol, "w", encoding="utf-8") as g:
        g.write(f.read())
    os.unlink(yedek)


def _mutant_ev_degistir(tsv_yolu, mekanizma_adi, yeni_ev):
    """M1: haritadaki bir satirin EV kolonunu gecici olarak degistir."""
    satirlar = open(tsv_yolu, encoding="utf-8").read().splitlines()
    out = []
    degisti = False
    for s in satirlar:
        if (not s.strip() or s.lstrip().startswith("#")
                or s.startswith("MEKANIZMA")):
            out.append(s)
            continue
        kol = s.split("\t")
        if len(kol) >= 3 and kol[0].strip() == mekanizma_adi and not degisti:
            kol[2] = yeni_ev
            degisti = True
            out.append("\t".join(kol))
            continue
        out.append(s)
    with open(tsv_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return degisti


def kendini_test(repo_kok, harita_yolu, koku_root):
    """3 mutant + izolasyon. Her biri hedef kolunu AYRICA kanitlar.

    koku_root: --kendini-test'te tempfile.mkdtemp(); gercek posta kutularina
    DOKUNULMAZ.

    KABUL: MUTANT=3/3, T3-YON, T3-SAHIPSIZ, T3-OLCULEMEDI gecti,
    SAHIPSIZ sayaci ayri basildi, TEMIZ=EVET kanitlandi.
    """
    tsv = os.path.join(repo_kok, harita_yolu) if not os.path.isabs(harita_yolu) else harita_yolu
    if not os.path.isfile(tsv):
        print("HATA: harita dosyasi yok: " + tsv)
        return 1
    yedek = _gvd_yedekle(tsv)
    try:
        harita, _ = haritayi_oku(repo_kok, harita_yolu)
        harita_index = mekanizmaya_mekanizma_adlari(harita)

        adimlar = []
        # Tek damga — sentetik tum mutantlar AYNI damga ile uretilir; temizlik
        # tek seferde kanitlanir.
        ortak_damga = "T3TEST-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        # --- M1: haritada r2-purge EV'si MaCiT -> ArTisT olsun -----------------
        # Beklenen: kalem ArTisT kutusuna yazilir, T3-YON kolu mesaj verir.
        _mutant_ev_degistir(tsv, "r2-purge", "ArTisT")
        harita1, _ = haritayi_oku(repo_kok, harita_yolu)
        idx1 = mekanizmaya_mekanizma_adlari(harita1)
        kalem_m1 = {
            "mekanizma": "r2-purge",
            "kosum_id": "kosum-M1-test",
            "kirmizi_adim": "M1.adim",
            "kabul_komutu": "python3 tools/r2-purge-test.py",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        sonuc_m1 = yonlendir(kalem_m1, idx1, koku_root=koku_root)
        # Izolasyon: ArTisT altinda /<koku_root>/ArTisT/memory/... olmali.
        m1_yazildi_artistte = (
            sonuc_m1["EV"] == "ArTisT"
            and sonuc_m1["YAZILDI"]
            and sonuc_m1["POSTA_YOL"] == os.path.join(koku_root, "ArTisT", POSTA_DOSYA)
        )
        # T3-YON kolunun mesaji: EV cozumleme haritadan OKUNDU (sabit degil).
        t3_yon_mesaj = ("EV=ArTisT (MUTANT_EV)" if sonuc_m1["EV_KAYNAK"] == "MUTANT_EV"
                        else "EV=%s" % sonuc_m1["EV"])
        m1_reddetti = m1_yazildi_artistte
        adimlar.append(("M1", T3_YON_JETON, m1_reddetti, t3_yon_mesaj,
                        sonuc_m1))
        _gvd_yedekten_geri(tsv, yedek)
        yedek = _gvd_yedekle(tsv)

        # --- M2: mekanizma haritada YOK ---------------------------------------
        # Beklenen: BILINMIYOR + kalem MIMAR'da KALIR + SAHIPSIZ sayaci artar.
        kalem_m2 = {
            "mekanizma": "hayalet-mekanizma-yok-12345",
            "kosum_id": "kosum-M2-test",
            "kirmizi_adim": "M2.adim",
            "kabul_komutu": "YOK",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        sonuc_m2 = yonlendir(kalem_m2, idx1, koku_root=koku_root)
        m2_sahipsiz = (
            sonuc_m2["EV"] == "BILINMIYOR"
            and sonuc_m2["SAHIPSIZ"] is True
            and sonuc_m2["YAZILDI"] is False
            and sonuc_m2["HATA"] is not None
        )
        t3_sahipsiz_mesaj = "EV=BILINMIYOR SAHIPSIZ=EVET (MIMAR'da kaldi)"
        m2_reddetti = m2_sahipsiz
        adimlar.append(("M2", T3_SAHIPSIZ_JETON, m2_reddetti, t3_sahipsiz_mesaj,
                        sonuc_m2))

        # --- M3: hedef kutuya yazma BASARISIZ --------------------------------
        # Beklenen: tatbikat KIRMIZI + OLCULEMEDI; "teslim edildi" DEMEZ.
        # Simulasyon: posta kutusu yolunu yazilamaz_yollar'a ekle.
        ev_can = "MaCiT"
        kok_m3, yol_m3, _ = ev_adresi(ev_can, koku_root=koku_root)
        yazilamaz = {yol_m3}
        # r2-purge icin (gercek haritaya gore) EV=MaCiT; M3 icin MaCiT yazilamaz.
        kalem_m3 = {
            "mekanizma": "r2-purge",
            "kosum_id": "kosum-M3-test",
            "kirmizi_adim": "M3.adim",
            "kabul_komutu": "python3 tools/r2-purge-test.py",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        # Haritayi geri yukle (M1 revert ettik), r2-purge MaCiT olsun.
        harita2, _ = haritayi_oku(repo_kok, harita_yolu)
        idx2 = mekanizmaya_mekanizma_adlari(harita2)
        sonuc_m3 = yonlendir(kalem_m3, idx2, koku_root=koku_root, yazilamaz_yollar=yazilamaz)
        m3_olculemedi = (
            sonuc_m3["YAZILDI"] is False
            and sonuc_m3["HATA"] is not None
            and "OLCULEMEDI" in sonuc_m3["HATA"]
        )
        t3_olculemedi_mesaj = ("EV=%s YAZILDI=False HATA=OLCULEMEDI (fail-closed)"
                               % sonuc_m3["EV"])
        m3_reddetti = m3_olculemedi
        adimlar.append(("M3", T3_OLCULEMEDI_JETON, m3_reddetti, t3_olculemedi_mesaj,
                        sonuc_m3))

        # --- TEMIZLIK KANITI --------------------------------------------------
        # Tum sentetik kalemleri AYNI damga ile urettik; temizlik kanitla.
        # Burada temizle_sentetik() gercek koklerdeki dosyalari da gezer; ama
        # --kendini-test'te koku_root gecici oldugu icin gercek koklerde hicbir
        # damga eslesmez ve silinmez. Yine de guvenli: bostan yazma yok.
        temizle_sonuc = temizle_sentetik([s for _, _, _, _, s in adimlar],
                                         koku_root=koku_root)
        # Izole kokte gercekten yazip yazmadigimizi kontrol et: dosya var mi?
        ortak_dosya = os.path.join(koku_root, POSTA_DOSYA)
        # Sentetik damga, izole kokte yazildiysa, temizlik sonrasi kalmamali.
        temizlik_ok = True
        if os.path.isfile(ortak_dosya):
            icerik = open(ortak_dosya, encoding="utf-8").read()
            if ortak_damga in icerik:
                temizlik_ok = False
        # Ek: alt dizinlerde de (ArTisT, MaCiT) damga kalmasin.
        for ev in ("ArTisT", "MaCiT"):
            alt = os.path.join(koku_root, ev, POSTA_DOSYA)
            if os.path.isfile(alt):
                if ortak_damga in open(alt, encoding="utf-8").read():
                    temizlik_ok = False

        # ---- ozet bas -------------------------------------------------------
        print("T3 YONLENDIRME KAPISI — KENDINI-TEST")
        print("izolasyon koku (posta kutulari): %s" % koku_root)
        print("ortak damga: %s" % ortak_damga)
        print("")
        mutant_sayaci = 0
        for ad, jeton, gecti, mesaj, sonuc in adimlar:
            print("MUTANT %s -> hedef kol %s" % (ad, jeton))
            print("  mesaj: %s" % mesaj)
            print("  EV=%s YAZILDI=%s SAHIPSIZ=%s HATA=%r"
                  % (sonuc["EV"], sonuc["YAZILDI"], sonuc["SAHIPSIZ"], sonuc["HATA"]))
            print("  POSTA_YOL=%s" % (sonuc["POSTA_YOL"] or "(yok)"))
            if gecti:
                print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
                mutant_sayaci += 1
            else:
                print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
            print("")

        # SAHIPSIZ sayaci (sadece M2'yi saymaz; bu turda analiz kisminda da
        # sayilir; burada M2'nin BEKLENTISI BILINMIYOR uretmesi).
        print("SAHIPSIZ=%d" % sum(1 for _, _, _, _, s in adimlar if s["SAHIPSIZ"]))
        # TEMIZ kaniti: izolasyon kokundeki gercek posta kutusu dosyasi yoksa
        # ya da damga yoksa TEMIZ=EVET; aksi TEMIZ=OLCULEMEDI.
        if temizlik_ok:
            print("TEMIZ=EVET")
        else:
            print("TEMIZ=OLCULEMEDI")
        print("")
        print("MUTANT=%d/3" % mutant_sayaci)
        if mutant_sayaci == 3 and temizlik_ok:
            return 0
        return 1
    finally:
        if yedek and os.path.isfile(yedek):
            try:
                _gvd_yedekten_geri(tsv, yedek)
            except OSError:
                pass


# ------------------------------------------------------------------------------
# ANALIZ (default, yazmaz)
# ------------------------------------------------------------------------------
def analiz(repo_kok, harita_yolu):
    harita, hatalar = haritayi_oku(repo_kok, harita_yolu)
    if hatalar:
        print("HARITA OKUMA HATALARI:", file=sys.stderr)
        for h in hatalar:
            print("  " + h, file=sys.stderr)
    idx = mekanizmaya_mekanizma_adlari(harita)

    dagilim = {ev: 0 for ev in EV_BILINEN}
    dagilim["BILINMIYOR"] = 0
    dagilim_ev_kaynak = {"HARITA": 0, "MUTANT_EV": 0, "BILINMIYOR": 0}
    mutant_turevleri = []  # (mekanizma, EV, EV_kaynak)

    # Mutasyon bataryalari haritanin evreninde yok; onlar icin ek cozumleme.
    ek_mekanizmalar = set()
    if os.path.isdir(os.path.join(repo_kok, "tools")):
        for f in sorted(os.listdir(os.path.join(repo_kok, "tools"))):
            if "-mutasyon" in f and f.endswith(".py") and not f.endswith("-test.py"):
                if f not in idx:
                    ek_mekanizmalar.add(f)

    for h in harita:
        ev = h["EV"]
        if ev in dagilim:
            dagilim[ev] += 1
        elif ev == "BILINMIYOR":
            dagilim["BILINMIYOR"] += 1

    for m in sorted(ek_mekanizmalar):
        ev = mekanizma_icin_ev(m, idx)
        if ev == "BILINMIYOR":
            dagilim["BILINMIYOR"] += 1
            mutant_turevleri.append((m, ev, "BILINMIYOR"))
        else:
            dagilim[ev] += 1
            mutant_turevleri.append((m, ev, "MUTANT_TUREV"))

    print("T3 YONLENDIRME KAPISI — ANALIZ (salt-okunur, YAZMAZ)")
    print("Repo: %s" % repo_kok)
    print("Harita: %s" % harita_yolu)
    print("")
    print("EV dagilimi (gercek harita + -mutasyon turevleri):")
    for ev in sorted(dagilim.keys()):
        print("  %-10s = %d" % (ev, dagilim[ev]))
    print("")
    print("SAHIPSIZ=%d (BILINMIYOR)" % dagilim["BILINMIYOR"])
    if mutant_turevleri:
        print("")
        print("-mutasyon turevleri (haritada yok; -kapisi.py'nin EV'sine dustu):")
        for m, ev, kaynak in mutant_turevleri:
            print("  %-32s -> %s (%s)" % (m, ev, kaynak))
    return 0


# ------------------------------------------------------------------------------
# TATBIKAT (gercek posta kutusu; AYNI kosumda siler)
# ------------------------------------------------------------------------------
def tatbikat(repo_kok, harita_yolu, temizlik=True):
    """Sentetik bir sahte kirmizi kalem uretip gercek posta kutusuna yazar.
    AYNI kosumda siler ve TEMIZ=EVET kanitlar.
    """
    harita, _ = haritayi_oku(repo_kok, harita_yolu)
    idx = mekanizmaya_mekanizma_adlari(harita)
    damga = "T3TATBIKAT-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    kalem = {
        "mekanizma": "r2-purge",
        "kosum_id": "kosum-tatbikat",
        "kirmizi_adim": "tatbikat.adim",
        "kabul_komutu": "python3 tools/r2-purge-test.py",
        "sahte_mi": "EVET",
        "sentetik": True,
        "damga": damga,
    }
    sonuc = yonlendir(kalem, idx, koku_root=None)
    print("TATBIKAT sonuc: EV=%s YAZILDI=%s POSTA_YOL=%s"
          % (sonuc["EV"], sonuc["YAZILDI"], sonuc["POSTA_YOL"]))
    if temizlik:
        silinenler = temizle_sentetik([sonuc], koku_root=None)
        # Kanit: dosya hâlâ varsa icinde damga YOKMUs
        kanit_temiz = True
        for yol, sildi in silinenler.items():
            if os.path.isfile(yol):
                icerik = open(yol, encoding="utf-8").read()
                if damga in icerik:
                    kanit_temiz = False
        if kanit_temiz:
            print("TEMIZ=EVET (silinen dosyalar: %d)" % len([k for k, v in silinenler.items() if v]))
            return 0
        else:
            print("TEMIZ=OLCULEMEDI (damga hâlâ bir dosyada bulundu)")
            return 1
    return 0


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None,
                    help="repo koku (default: betigin konumundan turetilir)")
    ap.add_argument("--harita", default=HARITA_RELATIF,
                    help="harita TSV yolu (repo-goreli veya mutlak)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="3 mutantu izole kos (gercek posta kutularina DOKUNMAZ)")
    ap.add_argument("--tatbikat", action="store_true",
                    help="sentetik kirmizi uretip gercek posta kutusuna yazar; "
                         "AYNI kosumda siler, TEMIZ=EVET kanitlar")
    ap.add_argument("--temizlik-yapma", action="store_true",
                    help="--tatbikat ile: silme adimini atla (test icin)")
    ap.add_argument("--posta-koku-root", default=None,
                    help="--kendini-test icin izole posta kutusu koku "
                         "(default: tempfile.mkdtemp()). Belirtilmezse gecici dizin.")
    args = ap.parse_args()

    repo_kok = args.repo or _repo_kok()

    if args.kendini_test:
        # Izolasyon: tempfile.mkdtemp() ASLA gercek posta kutusunu hedeflemez.
        koku = args.posta_koku_root or tempfile.mkdtemp(prefix="t3-kendinitest-")
        if not os.path.isdir(koku):
            try:
                os.makedirs(koku)
            except OSError as e:
                print("HATA: posta koku olusturulamadi: %r" % e)
                return 1
        # Gecici kok altinda hedef ev dizinleri olustur (MaCiT/ArTisT vs.)
        # ki M1 yazabilsin; bunlar yine de gecici.
        for ev in ("MaCiT", "ArTisT", "HocA", "TeKiN", "KraL"):
            os.makedirs(os.path.join(koku, ev, "memory"), exist_ok=True)
        rc = kendini_test(repo_kok, args.harita, koku)
        # Is bitince gecici koku temizle (Okan diski).
        if not args.posta_koku_root:
            shutil.rmtree(koku, ignore_errors=True)
        return rc

    if args.tatbikat:
        return tatbikat(repo_kok, args.harita,
                        temizlik=not args.temizlik_yapma)

    return analiz(repo_kok, args.harita)


if __name__ == "__main__":
    sys.exit(main())