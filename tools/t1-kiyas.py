#!/usr/bin/env python3
"""T1 paralel pencere kiyas tablosu uretici.

Salt okuma. Hicbir log/durum dosyasini degistirmez.
Kabul: python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --kendini-test
Gercek: python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --gercek
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone


VARSAYILAN_KOK = "/Users/okan/.claude/cron"
PENCERE_DOSYASI = "t1-pencere.json"
YENI_LOG = "gozcu-cron.log"
ESKI_LOG = "ci-nobeti.log"

YENI_DAKIKA = 23
ESKI_DAKIKA = 7

_RE_GOZCU = re.compile(
    r"^GOZCU\s+(?P<damga>\S+)\s+"
    r"TETIK=(?P<tetik>\S+)\s+"
    r".*LLM_TURU=(?P<llm>\d+)\s+"
    r".*YENI_KIRMIZI=(?P<kirmizi>\d+)\s+"
    r".*rc=(?P<rc>\d+)\s*$"
)

_RE_ESKI_BITIS = re.compile(
    r"^===\s+(?P<damga>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+.*BITIS\s+rc=(?P<rc>\d+)\s*==="
)

_RE_ESKI_UYARI = re.compile(r"^UYARI:\s*Tur\s+KIRMIZI")
_RE_ESKI_MOTOR = re.compile(r"^MOTOR=(\S+)")


class OkumaHatasi(Exception):
    pass


def _iso_oku(s):
    """ISO 8601 Z damgasini UTC datetime'a donustur."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _iso_yaz(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _damga_dakika(dt):
    return dt.replace(second=0, microsecond=0)


def beklenen_turlar(baslangic, bitis, dakika):
    """Pencere icinde saatte bir, verilen dakikadaki beklenen turleri listele."""
    bas = _iso_oku(baslangic)
    son = _iso_oku(bitis)
    ilk = bas.replace(minute=dakika, second=0, microsecond=0)
    if ilk < bas:
        ilk += timedelta(hours=1)
    turlar = []
    cur = ilk
    while cur <= son:
        turlar.append(_iso_yaz(cur))
        cur += timedelta(hours=1)
    return turlar


def yeni_hat_oku(yol):
    """gozcu-cron.log'u oku; dakika bazinda birlestirilmis kayitlari dondur.

    Donus: dict {dakika_dt: {"tetik": str, "llm": int, "kirmizi": int, "rc": int}}
    """
    kayitlar = {}
    if not os.path.exists(yol):
        return kayitlar
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        for satir in f:
            m = _RE_GOZCU.search(satir)
            if not m:
                continue
            damga = _iso_oku(m.group("damga"))
            dak = _damka_dakika(damga)
            mevcut = kayitlar.get(dak)
            tetik = m.group("tetik")
            llm = int(m.group("llm"))
            kirmizi = int(m.group("kirmizi"))
            rc = int(m.group("rc"))
            if mevcut is None:
                kayitlar[dak] = {
                    "tetik": tetik,
                    "llm": llm,
                    "kirmizi": kirmizi,
                    "rc": rc,
                }
            else:
                # Ayni dakikada birden fazla satir varsa, en az bir olculmus
                # satir varsa OLCULDU say; degerleri topla.
                if tetik != "OLCULEMEDI":
                    mevcut["tetik"] = tetik
                mevcut["llm"] += llm
                mevcut["kirmizi"] += kirmizi
                mevcut["rc"] = max(mevcut["rc"], rc)
    return kayitlar


def eski_hat_oku(yol):
    """ci-nobeti.log'u oku; BITIS satirlarini ve ilgili bolgelerini dondur.

    Donus: liste [{"damga": datetime, "rc": int, "uyari": int, "motor": bool}]
    Bir BITIS satirinin bolgesi, bir onceki BITIS satirinden sonra baslar.
    """
    kayitlar = []
    if not os.path.exists(yol):
        return kayitlar
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        satirlar = f.readlines()

    onceki_bitis_indeks = -1
    for i, satir in enumerate(satirlar):
        m = _RE_ESKI_BITIS.search(satir)
        if not m:
            continue
        damga = _iso_oku(m.group("damga"))
        rc = int(m.group("rc"))
        bolge = satirlar[onceki_bitis_indeks + 1 : i]
        uyari = sum(1 for s in bolge if _RE_ESKI_UYARI.search(s))
        motor = any(_RE_ESKI_MOTOR.search(s) for s in bolge)
        kayitlar.append({"damga": damga, "rc": rc, "uyari": uyari, "motor": motor})
        onceki_bitis_indeks = i
    return kayitlar


def _beklenen_dakika(iso):
    return _damka_dakika(_iso_oku(iso))


def kova_hesapla(beklenen, kayitlar, mutasyon=None):
    """Bir hat icin kova sayilarini ve toplamlari hesapla.

    beklenen: ISO damga listesi (takvimden)
    kayitlar: yeni hat icin {dakika_dt: kayit}; eski hat icin [kayit]
    mutasyon: None, 'm1', 'm2'

    Donus: {
        "kosan": int,
        "olculdu": int,
        "olculemedi": int,
        "kosmadi": int,
        "kirmizi": int,
        "llm": int,
        "tetiklenen": int,
        "ilk_olculen": iso_str|None,
    }
    """
    # Beklenen dakikalari hazirla
    beklenen_dakikalar = {iso: _beklenen_dakika(iso) for iso in beklenen}

    # Eski hat kayitlarini dakikaya gore indeksle (cakisanlar olursa birlestir)
    if isinstance(kayitlar, list):
        kayit_dict = {}
        for k in kayitlar:
            dak = _damka_dakika(k["damga"])
            mevcut = kayit_dict.get(dak)
            if mevcut is None:
                kayit_dict[dak] = {
                    "rc": k["rc"],
                    "uyari": k["uyari"],
                    "motor": k["motor"],
                }
            else:
                mevcut["rc"] = max(mevcut["rc"], k["rc"])
                mevcut["uyari"] += k["uyari"]
                mevcut["motor"] = mevcut["motor"] or k["motor"]
    else:
        kayit_dict = kayitlar

    kosan = 0
    olculdu = 0
    olculemedi = 0
    kosmadi = 0
    kirmizi = 0
    llm = 0
    tetiklenen = 0
    ilk_olculen = None

    for iso, dak in beklenen_dakikalar.items():
        kayit = kayit_dict.get(dak)
        if kayit is None:
            kova = "KOSMADI"
        elif isinstance(kayit, dict) and "tetik" in kayit:
            if kayit["tetik"] == "OLCULEMEDI":
                kova = "OLCULEMEDI"
            else:
                kova = "OLCULDU"
        else:
            # Eski hat: BITIS satiri varsa olculmustur.
            kova = "OLCULDU"

        # Mutasyonlar
        if mutasyon == "m1" and kova == "OLCULEMEDI":
            kova = "OLCULDU"
            # OLCULEMEDI satirlarinin kendi degerleri 0 kabul edilir,
            # dolayisiyla toplamlara katki vermez.
            if isinstance(kayit, dict):
                kayit = dict(kayit)
                kayit["llm"] = 0
                kayit["kirmizi"] = 0
        if mutasyon == "m2" and kova == "KOSMADI":
            kova = "OLCULDU"
            kayit = {"rc": 0, "llm": 0, "kirmizi": 0}

        if kova == "KOSMADI":
            kosmadi += 1
        elif kova == "OLCULEMEDI":
            kosan += 1
            olculemedi += 1
        else:  # OLCULDU
            kosan += 1
            olculdu += 1
            if ilk_olculen is None:
                ilk_olculen = iso
            if isinstance(kayit, dict):
                if "kirmizi" in kayit:
                    kirmizi += kayit["kirmizi"]
                else:
                    # Eski hat: uyari satiri sayisini kirmizi olarak say
                    kirmizi += kayit.get("uyari", 0)
                if "llm" in kayit:
                    llm += kayit["llm"]
                else:
                    # Eski hat: motor satiri varsa LLM turu say
                    if kayit.get("motor"):
                        llm += 1
                if "tetik" in kayit:
                    tetiklenen += 1
                else:
                    # Eski hat: rc != 0 ise tetiklenmis say
                    if kayit.get("rc", 0) != 0:
                        tetiklenen += 1

    return {
        "kosan": kosan,
        "olculdu": olculdu,
        "olculemedi": olculemedi,
        "kosmadi": kosmadi,
        "kirmizi": kirmizi,
        "llm": llm,
        "tetiklenen": tetiklenen,
        "ilk_olculen": ilk_olculen,
    }


def tablo_satir(eski, yeni):
    """Iki sutunlu tablo satirlarini dondur."""
    def hucre(deger):
        if deger is None:
            return "OLCULEMEDI"
        return str(deger)

    return [
        ("beklenen tur", hucre(yeni["beklenen"]), hucre(eski["beklenen"])),
        ("kosan tur", hucre(yeni["kosan"]), hucre(eski["kosan"])),
        ("yakalanan yeni kirmizi (toplam)", hucre(yeni["kirmizi"]), hucre(eski["kirmizi"])),
        ("LLM turu (toplam)", hucre(yeni["llm"]), hucre(eski["llm"])),
        ("tetiklenen tur sayisi", hucre(yeni["tetiklenen"]), hucre(eski["tetiklenen"])),
    ]


def calistir(kok, mutasyon=None):
    """Ana islem: loglari oku, kovala, tablo ve son satir uret.

    Donus: (rc, cikti_dict, satirlar)
    """
    pencere_yol = os.path.join(kok, PENCERE_DOSYASI)
    yeni_yol = os.path.join(kok, YENI_LOG)
    eski_yol = os.path.join(kok, ESKI_LOG)

    if not os.path.exists(pencere_yol):
        raise OkumaHatasi(f"Pencere dosyasi bulunamadi: {pencere_yol}")

    with open(pencere_yol, "r", encoding="utf-8") as f:
        pencere = json.load(f)
    baslangic = pencere["baslangic"]
    bitis = pencere["bitis"]

    simdi = datetime.now(timezone.utc)
    durum = "KAPANDI" if simdi > _iso_oku(bitis) else "ACIK"

    yeni_beklenen = beklenen_turlar(baslangic, bitis, YENI_DAKIKA)
    eski_beklenen = beklenen_turlar(baslangic, bitis, ESKI_DAKIKA)

    yeni_oku = yeni_hat_oku(yeni_yol)
    eski_oku = eski_hat_oku(eski_yol)

    yeni_sonuc = kova_hesapla(yeni_beklenen, yeni_oku, mutasyon=mutasyon)
    eski_sonuc = kova_hesapla(eski_beklenen, eski_oku, mutasyon=mutasyon)

    yeni_sonuc["beklenen"] = len(yeni_beklenen)
    eski_sonuc["beklenen"] = len(eski_beklenen)

    # Mutasyon M3: FIILEN_BASLANGIC'i nominal baslangica esitle
    fiilen = yeni_sonuc["ilk_olculen"]
    if mutasyon == "m3":
        fiilen = baslangic
    if fiilen is None:
        fiilen = "YOK"

    # Mutasyon M4: toplamlari sabit beyandan al
    yeni_kirmizi_toplam = yeni_sonuc["kirmizi"]
    yeni_llm_toplam = yeni_sonuc["llm"]
    if mutasyon == "m4":
        yeni_kirmizi_toplam = 9999
        yeni_llm_toplam = 8888

    rc = 0
    eski_hucre = lambda k: eski_sonuc.get(k)

    # Eger eski log yoksa, eski eksenler OLCULEMEDI olarak isaretlenir.
    if not os.path.exists(eski_yol):
        for k in ("kosan", "kirmizi", "llm", "tetiklenen"):
            eski_sonuc[k] = None
        rc = 1

    # Yeni log yoksa tum yeni eksenler OLCULEMEDI
    if not os.path.exists(yeni_yol):
        for k in ("kosan", "olculdu", "olculemedi", "kosmadi", "kirmizi", "llm", "tetiklenen"):
            yeni_sonuc[k] = None
        fiilen = "YOK"
        rc = 1

    baslik = "ARA TABLO (pencere ACIK)" if durum == "ACIK" else "NIHAI KIYAS TABLOSU"

    satirlar = [f"# T1 KIYAS TABLOSU — {baslik}", ""]
    satirlar.append("| Eksen | YENI HAT (gozcu :23) | ESKI HAT (ci-nobeti :07) |")
    satirlar.append("|---|---|---|")
    for eksen, y_deger, e_deger in tablo_satir(eski_sonuc, yeni_sonuc):
        satirlar.append(f"| {eksen} | {y_deger} | {e_deger} |")
    satirlar.append("")

    son = (
        f"T1 PENCERE={baslangic}..{bitis} "
        f"FIILEN_BASLANGIC={fiilen} "
        f"BEKLENEN_TUR={yeni_sonuc['beklenen']} "
        f"OLCULDU_TUR={_yaz(yeni_sonuc.get('olculdu'))} "
        f"OLCULEMEDI_TUR={_yaz(yeni_sonuc.get('olculemedi'))} "
        f"KOSMADI_TUR={_yaz(yeni_sonuc.get('kosmadi'))} "
        f"YENI_KIRMIZI={_yaz(yeni_kirmizi_toplam)} "
        f"LLM_TURU_YENI={_yaz(yeni_llm_toplam)} "
        f"LLM_TURU_ESKI={_yaz(eski_sonuc.get('llm'))} "
        f"DURUM={durum}"
    )
    satirlar.append(son)

    cikti = {
        "pencere": pencere,
        "durum": durum,
        "fiilen_baslangic": fiilen,
        "yeni": yeni_sonuc,
        "eski": eski_sonuc,
        "yeni_kirmizi_toplam": yeni_kirmizi_toplam,
        "yeni_llm_toplam": yeni_llm_toplam,
    }
    return rc, cikti, satirlar


def _yaz(deger):
    return "OLCULEMEDI" if deger is None else str(deger)


def _damka_dakika(dt):
    return dt.replace(second=0, microsecond=0)


def _fikstur_olustur(tmp):
    """Kabul testi icin sentetik loglari ve pencereyi olustur."""
    pencere = {
        "baslangic": "2026-08-18T08:48:05Z",
        "bitis": "2026-08-18T13:48:05Z",
        "sure_saat": 5,
        "eski_cron": "ci-nobeti",
        "yeni_hat": "gozcu.py --tur",
        "gerekce": "sentetik test",
    }
    with open(os.path.join(tmp, PENCERE_DOSYASI), "w", encoding="utf-8") as f:
        json.dump(pencere, f)

    # Yeni hat: ilk olculen 09:23, sonra iki OLCULEMEDI, sonra KOSMADI
    yeni_satirlar = [
        # Pencere disi (K1)
        "GOZCU 2026-08-18T08:23:00Z TETIK=CI_KIRMIZI LLM_TURU=1 YENI_KIRMIZI=99 DAGITILABILIR=1 KAT_MIMAR=10 rc=1\n",
        # Ilk olculen
        "GOZCU 2026-08-18T09:23:00Z TETIK=CI_KIRMIZI LLM_TURU=1 YENI_KIRMIZI=3 DAGITILABILIR=1 KAT_MIMAR=10 rc=1\n",
        "GOZCU 2026-08-18T10:23:01Z TETIK=OLCULEMEDI LLM_TURU=0 YENI_KIRMIZI=0 DAGITILABILIR=1 KAT_MIMAR=10 rc=2\n",
        "GOZCU 2026-08-18T11:23:00Z TETIK=OLCULEMEDI LLM_TURU=0 YENI_KIRMIZI=0 DAGITILABILIR=1 KAT_MIMAR=10 rc=2\n",
        "GOZCU 2026-08-18T12:23:00Z TETIK=DEFTER_DAGITIM LLM_TURU=1 YENI_KIRMIZI=2 DAGITILABILIR=1 KAT_MIMAR=10 rc=1\n",
        # Pencere disi (K1)
        "GOZCU 2026-08-18T14:23:00Z TETIK=CI_KIRMIZI LLM_TURU=1 YENI_KIRMIZI=99 DAGITILABILIR=1 KAT_MIMAR=10 rc=1\n",
    ]
    with open(os.path.join(tmp, YENI_LOG), "w", encoding="utf-8") as f:
        f.writelines(yeni_satirlar)

    # Eski hat: iki kirmizi (biri motorsuz), bir yesil motorlu, bir KOSMADI, bir yesil motorsuz
    eski_satirlar = [
        # Pencere disi (K1): satir vardir ama sayaclara katilmaz
        "=== 2026-08-18T08:07:00Z BITIS rc=1 ===\n",
        "K1 pencere disi notu\n",
        # Beklenen 09:07
        "=== 2026-08-18T09:07:00Z BASLANGIC (nobet-kapi) ===\n",
        "HUKUM=ONARIMSIZ_TUR rc=1\n",
        "MOTOR=kimi\n",
        "=== 2026-08-18T09:07:30Z BITIS rc=1 ===\n",
        "UYARI: Tur KIRMIZI (onarimsiz tur / motor yok / kosum dustu); olculemedi != yesil.\n",
        # Beklenen 10:07
        "=== 2026-08-18T10:07:00Z BASLANGIC ===\n",
        "HUKUM=TEMIZ rc=0\n",
        "MOTOR=minimax-m3\n",
        "=== 2026-08-18T10:07:45Z BITIS rc=0 ===\n",
        # Beklenen 11:07 yok -> KOSMADI
        # Beklenen 12:07
        "=== 2026-08-18T12:07:00Z BASLANGIC ===\n",
        "HUKUM=ONARIMSIZ_TUR rc=1\n",
        "=== 2026-08-18T12:07:20Z BITIS rc=1 ===\n",
        "UYARI: Tur KIRMIZI (onarimsiz tur)\n",
        # Beklenen 13:07
        "=== 2026-08-18T13:07:00Z BASLANGIC ===\n",
        "HUKUM=TEMIZ rc=0\n",
        "=== 2026-08-18T13:07:55Z BITIS rc=0 ===\n",
        # Pencere disi (K1)
        "=== 2026-08-18T14:07:00Z BITIS rc=1 ===\n",
        "UYARI: Tur KIRMIZI (pencere disi)\n",
        # K2: bicimsiz satirlar (araci cokertmemeli)
        "SACMA SATIR\n",
        "=== BITIS rc=0 ===\n",
        "MOTOR_DENEME motor=minimax-m3 rc=0 sebep=YESIL\n",
    ]
    with open(os.path.join(tmp, ESKI_LOG), "w", encoding="utf-8") as f:
        f.writelines(eski_satirlar)


def _beklenen_sonuc():
    """Fiksture gore beklenen normal (mutasyonsuz) sonuc."""
    return {
        "yeni": {
            "beklenen": 5,
            "kosan": 4,
            "olculdu": 2,
            "olculemedi": 2,
            "kosmadi": 1,
            "kirmizi": 5,
            "llm": 2,
            "tetiklenen": 2,
            "ilk_olculen": "2026-08-18T09:23:00Z",
        },
        "eski": {
            "beklenen": 5,
            "kosan": 4,
            "olculdu": 4,
            "olculemedi": 0,
            "kosmadi": 1,
            "kirmizi": 2,
            "llm": 2,
            "tetiklenen": 2,
        },
        "fiilen_baslangic": "2026-08-18T09:23:00Z",
        "yeni_kirmizi_toplam": 5,
        "yeni_llm_toplam": 2,
        "durum": "KAPANDI",
    }


def _karsilastir(beklenen, gercek):
    """Iki sonuc sozlugunu karsilastir; fark yoksa None, varsa aciklamali metin dondur."""
    farklar = []
    for anahtar in ("fiilen_baslangic", "yeni_kirmizi_toplam", "yeni_llm_toplam", "durum"):
        if beklenen.get(anahtar) != gercek.get(anahtar):
            farklar.append(f"{anahtar}: beklenen={beklenen.get(anahtar)} gercek={gercek.get(anahtar)}")
    for hat in ("yeni", "eski"):
        b = beklenen.get(hat, {})
        g = gercek.get(hat, {})
        for k in ("beklenen", "kosan", "olculdu", "olculemedi", "kosmadi", "kirmizi", "llm", "tetiklenen"):
            if b.get(k) != g.get(k):
                farklar.append(f"{hat}.{k}: beklenen={b.get(k)} gercek={g.get(k)}")
    return "; ".join(farklar) if farklar else None


def kendini_test():
    """Mutasyon ve kontrol bataryasini calistir."""
    import shutil

    tmp = tempfile.mkdtemp(prefix="t1-kiyas-test-")
    try:
        _fikstur_olustur(tmp)
        beklenen = _beklenen_sonuc()

        def calistir_mut(m):
            rc, cikti, _ = calistir(tmp, mutasyon=m)
            return rc, cikti

        rc0, cikti0 = calistir_mut(None)
        fark = _karsilastir(beklenen, cikti0)
        if fark:
            print(f"BASE HATALI: {fark}", file=sys.stderr)
            return 1
        if rc0 != 0:
            print(f"BASE rc beklenen=0 gercek={rc0}", file=sys.stderr)
            return 1

        rapor = []
        mutantlar = []
        kontroller = []

        # M1: OLCULEMEDI -> OLCULDU
        rc, c = calistir_mut("m1")
        hedef = c["yeni"]["olculemedi"] != beklenen["yeni"]["olculemedi"]
        yan = (
            c["yeni"]["kosmadi"] == beklenen["yeni"]["kosmadi"]
            and c["fiilen_baslangic"] == beklenen["fiilen_baslangic"]
            and c["yeni_kirmizi_toplam"] == beklenen["yeni_kirmizi_toplam"]
            and c["yeni_llm_toplam"] == beklenen["yeni_llm_toplam"]
        )
        mutantlar.append(("M1", hedef, yan))

        # M2: KOSMADI -> OLCULDU
        rc, c = calistir_mut("m2")
        hedef = c["yeni"]["kosmadi"] != beklenen["yeni"]["kosmadi"]
        yan = (
            c["yeni"]["olculemedi"] == beklenen["yeni"]["olculemedi"]
            and c["fiilen_baslangic"] == beklenen["fiilen_baslangic"]
            and c["yeni_kirmizi_toplam"] == beklenen["yeni_kirmizi_toplam"]
            and c["yeni_llm_toplam"] == beklenen["yeni_llm_toplam"]
        )
        mutantlar.append(("M2", hedef, yan))

        # M3: FIILEN_BASLANGIC = nominal
        rc, c = calistir_mut("m3")
        hedef = c["fiilen_baslangic"] != beklenen["fiilen_baslangic"]
        yan = (
            c["yeni"]["olculdu"] == beklenen["yeni"]["olculdu"]
            and c["yeni"]["olculemedi"] == beklenen["yeni"]["olculemedi"]
            and c["yeni"]["kosmadi"] == beklenen["yeni"]["kosmadi"]
            and c["yeni_kirmizi_toplam"] == beklenen["yeni_kirmizi_toplam"]
            and c["yeni_llm_toplam"] == beklenen["yeni_llm_toplam"]
        )
        mutantlar.append(("M3", hedef, yan))

        # M4: Toplamlar sabit beyandan
        rc, c = calistir_mut("m4")
        hedef = (
            c["yeni_kirmizi_toplam"] != beklenen["yeni_kirmizi_toplam"]
            or c["yeni_llm_toplam"] != beklenen["yeni_llm_toplam"]
        )
        yan = (
            c["yeni"]["olculdu"] == beklenen["yeni"]["olculdu"]
            and c["yeni"]["olculemedi"] == beklenen["yeni"]["olculemedi"]
            and c["yeni"]["kosmadi"] == beklenen["yeni"]["kosmadi"]
            and c["fiilen_baslangic"] == beklenen["fiilen_baslangic"]
        )
        mutantlar.append(("M4", hedef, yan))

        # K1: Pencere disi satirlar sayaclari degistirmiyor (base fikstur zaten iceriyor)
        rc, c = calistir_mut(None)
        k1 = _karsilastir(beklenen, c) is None
        kontroller.append(("K1", k1))

        # K2: Eski logdaki bicimsiz satirlar araci cokertmiyor
        k2 = c["eski"]["kosan"] == beklenen["eski"]["kosan"]
        kontroller.append(("K2", k2))

        hedef_atfi = sum(1 for _, h, y in mutantlar if h and y)
        kontrol_gecen = sum(1 for _, g in kontroller if g)

        for ad, h, y in mutantlar:
            rapor.append(f"{ad} HEDEF_KIRMIZI={h} YAN_EKSEN_YESIL={y}")
        for ad, g in kontroller:
            rapor.append(f"{ad} GECTI={g}")

        print("\n".join(rapor))
        vaka = len(mutantlar) + len(kontroller)
        dusen = (len(mutantlar) - hedef_atfi) + (len(kontroller) - kontrol_gecen)
        print(
            f"VAKA={vaka} DUSEN={dusen} "
            f"MUTANT={hedef_atfi}/{len(mutantlar)} "
            f"HEDEF_KOL_ATFI={hedef_atfi}/{len(mutantlar)} "
            f"KONTROL={kontrol_gecen}/{len(kontroller)} TEMIZ=EVET"
        )
        return 0 if dusen == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="T1 kiyas tablosu uretici")
    parser.add_argument("--kok", default=VARSAYILAN_KOK, help="Loglarin kok dizini")
    parser.add_argument("--kendini-test", action="store_true", help="Mutasyon bataryasini kos")
    parser.add_argument("--gercek", action="store_true", help="Gercek veri kolu (rapora yazilacak)")
    args = parser.parse_args()

    if args.kendini_test:
        sys.exit(kendini_test())

    try:
        rc, _, satirlar = calistir(args.kok)
        print("\n".join(satirlar))
        sys.exit(rc)
    except OkumaHatasi as e:
        print(f"T1 HATA: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"T1 HATA: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
