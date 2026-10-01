#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTAK KUTUDA OKSUZ GOVDE OLCUM KOLU (K424) — SALT-OKUNUR.

    python3 tools/kutu-oksuz-nobeti.py                  # gercek kutu
    python3 tools/kutu-oksuz-nobeti.py --kutu <yol>     # baska bir kutu kopyasi

Her kosumda ilk satir birebir `KUTU_OKSUZ_GOVDE=<n>` (n = tam sayi, ya da olculemediyse
`OLCULEMEDI` / kutu bu makinede yoksa `MAKINEDE_YOK`). Sayi hicbir zaman "olcemedim"
halinde 0 basmaz.

NEDEN VAR (K424, 26 Eyl 2026, OLCULDU): iki MaCiT kapanisi kutunun DIBINE `## `
basliksiz eklendi. Rotasyon araci (`kutu-arsivle.py`) bunu D11 ile gordu ve DURDU
(`BUTUNLUK KIRMIZI — HICBIR SEY YAZILMADI`, rc=1), ama gorunur tek iz push kancasinin
fail-open satiriydi (`!! POSTA KUTUSU arsivlenemedi (push DEVAM ediyor)`). 09:00
advisor kutuyu 489/500 SAYDI ama oksuz govdeyi saymadi; gozcu satirinda kutu butunlugu
alani yoktu. Kutu 500 satira varsa rotasyon D11'de durdugu icin kota kapisi evin HER
commit'ini kilitler ve kilidi acan arac calismaz — elle onarima kadar. Bu arac o erken
uyariyi (tavan ASILMADAN once) tek satirlik, grep'lenebilir bir olcume cevirir.

KOPYA YOK: tespit tanimi `kutu-arsivle.py::oksuz_govdeler` / `ayrac_sayisi` /
`frontmatter_sonu`dur ve BURADA yeniden yazilmaz (ikiz tanim sessizce ayrisir). Bu arac
yalnizca onlari cagirir, kutuyu OKUR, hicbir sey yazmaz.

CIKIS KODU (yayin-kapisi ile ayni uc-jeton politikasi):
    0  TEMIZ  (n=0)  ya da  MAKINEDE_YOK (kutunun hafiza dizini bu makinede hic yok:
                     CI / kardes makine — `defter-kota-kapisi` KUTU_MAKINEDE_YOK emsali)
    1  KIRMIZI       (n>0: BASLIKSIZ dolu bolut var)
    2  OLCULEMEDI    (dosya yok/okunamadi/UTF-8 degil, yarim frontmatter, sahip arac
                     yuklenemedi YA DA kutuda ayrac (`---`) yok ve 2+ blok var)

KORLUK (bilerek 0 basilmayan hal): ayracsiz kutuda dusen baslik govdeleri BIRLESTIRIR ve
yapisal iz birakmaz; `kutu-arsivle.py` bunu `EKSEN_KOR=oksuz_govde_kutu` diye beyan eder.
Burada ayni hal `OLCULEMEDI` olur — "0 = temiz" DEGIL "olculemedi".
"""
import importlib.util
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))

RC_TEMIZ = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 2

HAL_TEMIZ = "TEMIZ"
HAL_OKSUZ = "OKSUZ"
HAL_OLCULEMEDI = "OLCULEMEDI"
HAL_MAKINEDE_YOK = "MAKINEDE_YOK"

HAL_RC = {
    HAL_TEMIZ: RC_TEMIZ,
    HAL_MAKINEDE_YOK: RC_TEMIZ,
    HAL_OKSUZ: RC_KIRMIZI,
    HAL_OLCULEMEDI: RC_OLCULEMEDI,
}

# Ekrana basilan ornek sayisi tavani (gurultu sinirla; SAYI her zaman tamdir).
ORNEK_TAVANI = 5


def _arsivle_modulu():
    """(modul, hata). tools/kutu-arsivle.py'yi bu dosyanin YANINDAN yukler."""
    yol = os.path.join(TOOLS, "kutu-arsivle.py")
    if not os.path.exists(yol):
        return None, "tools/kutu-arsivle.py YOK (tespit tanimi sahibi)"
    try:
        spec = importlib.util.spec_from_file_location("kutu_arsivle_oksuz", yol)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    except Exception as e:
        return None, "kutu-arsivle.py yuklenemedi: %s: %s" % (type(e).__name__, e)
    return m, None


def olc(kutu_yolu=None):
    """Olcum sonucu: {hal, n, ornekler, ayrac, blok, yol, hata}. ASLA firlatmaz."""
    sonuc = {"hal": HAL_OLCULEMEDI, "n": None, "ornekler": [], "ayrac": None,
             "blok": None, "yol": kutu_yolu, "hata": None}
    m, hata = _arsivle_modulu()
    if m is None:
        sonuc["hata"] = hata
        return sonuc
    yol = kutu_yolu or os.environ.get("PRUVO_KUTU_YOLU") or m.KUTU_VARSAYILAN
    sonuc["yol"] = yol
    if not os.path.exists(yol):
        if not os.path.isdir(os.path.dirname(yol)):
            # Hafiza dizininin kendisi yok: bu makinenin kutusu degil (CI / kosucu).
            sonuc["hal"] = HAL_MAKINEDE_YOK
            return sonuc
        sonuc["hata"] = "kutu dosyasi YOK (hafiza dizini var): %s" % yol
        return sonuc
    metin, hata = m.oku(yol)
    if metin is None:
        sonuc["hata"] = hata
        return sonuc
    _, fm_hata = m.frontmatter_sonu(metin.splitlines(keepends=True))
    if fm_hata:
        sonuc["hata"] = fm_hata
        return sonuc
    oksuz = m.oksuz_govdeler(metin)
    ayrac = m.ayrac_sayisi(metin)
    blok = m.blok_sayisi(metin)
    sonuc.update(n=len(oksuz), ornekler=oksuz, ayrac=ayrac, blok=blok)
    if oksuz:
        sonuc["hal"] = HAL_OKSUZ
    elif ayrac == 0 and blok > 1:
        # Ayracsiz kutuda dusen baslik YAPISAL iz birakmaz -> 0 "temiz" degil "kor".
        sonuc["n"] = None
        sonuc["hata"] = ("kutuda ayrac (`---`) YOK ve %d blok var -> dusen baslik bu "
                         "eksende YAPISAL OLARAK gorunmez (EKSEN_KOR)" % blok)
    else:
        sonuc["hal"] = HAL_TEMIZ
    return sonuc


def _sayi_metni(s):
    if s["hal"] == HAL_MAKINEDE_YOK:
        return "MAKINEDE_YOK"
    if s["n"] is None:
        return "OLCULEMEDI"
    return str(s["n"])


def cikti_satirlari(s):
    """CLI'nin stdout satirlari (ilk satir sozlesmedir: KUTU_OKSUZ_GOVDE=<n>)."""
    satirlar = ["KUTU_OKSUZ_GOVDE=%s" % _sayi_metni(s)]
    if s["hal"] == HAL_MAKINEDE_YOK:
        satirlar.append("KUTU: hafiza dizini bu makinede YOK (%s) -> bu makinenin kutusu "
                        "degil; olculmedi" % s["yol"])
    elif s["hal"] == HAL_OLCULEMEDI:
        satirlar.append("OLCULEMEDI: %s" % s["hata"])
    else:
        satirlar.append("KUTU=%s ayrac=%s blok=%s" % (s["yol"], s["ayrac"], s["blok"]))
    for satir_no, ornek in s["ornekler"][:ORNEK_TAVANI]:
        satirlar.append("  ! KUTU %d. satir: BASLIKSIZ dolu bolut | %s" % (satir_no, ornek))
    if len(s["ornekler"]) > ORNEK_TAVANI:
        satirlar.append("  ... +%d bulgu daha (sayi tamdir)" % (len(s["ornekler"]) - ORNEK_TAVANI))
    if s["hal"] == HAL_OKSUZ:
        satirlar.append(
            "NE YAPILMALI: gövde(ler)i BIREBIR koruyup `## ` baslik ekle ve tarih sirasina "
            "tasi (K424 ornek onarimi); `python3 tools/kutu-arsivle.py --kuru` "
            "`oksuz_govde_kutu=0` basana kadar rotasyon calismaz ve kutu 500 satira "
            "varirsa kota kapisi evin HER commit'ini kilitler.")
    hukum = {HAL_TEMIZ: "YESIL", HAL_MAKINEDE_YOK: "MAKINEDE_YOK",
             HAL_OKSUZ: "KIRMIZI", HAL_OLCULEMEDI: "OLCULEMEDI"}[s["hal"]]
    satirlar.append("HUKUM: %s (rc=%d)" % (hukum, HAL_RC[s["hal"]]))
    return satirlar


def satirlar(kutu_yolu=None):
    """durum.py panosu icin girintili satirlar (pano ASLA patlamaz)."""
    try:
        s = olc(kutu_yolu)
    except Exception as e:                       # olc() firlatmaz; kemer + atkı
        return ["  ⚪ ÖLÇÜLEMEDİ: kutu oksuz govde nobetcisi coktu (%s) — 'sorun yok' "
                "demek DEGILDIR." % type(e).__name__]
    if s["hal"] == HAL_OKSUZ:
        cikti = ["  🔴 KUTU_OKSUZ_GOVDE=%d — kutuda BASLIKSIZ dolu bolut var; rotasyon "
                 "D11'de DURUR, kutu 500'e varirsa evin commit'i KILITLENIR." % s["n"]]
        for satir_no, ornek in s["ornekler"][:ORNEK_TAVANI]:
            cikti.append("      satir %d | %s" % (satir_no, ornek))
        cikti.append("  (onarim: gövdeyi BIREBIR koru + `## ` baslik ekle + tarih sirasina "
                     "tasi; dogrula: python3 tools/kutu-arsivle.py --kuru)")
        return cikti
    if s["hal"] == HAL_TEMIZ:
        return ["  🟢 KUTU_OKSUZ_GOVDE=0 (ayrac=%s · blok=%s)" % (s["ayrac"], s["blok"])]
    if s["hal"] == HAL_MAKINEDE_YOK:
        return ["  ⚪ KUTU_OKSUZ_GOVDE=MAKINEDE_YOK — hafiza dizini bu makinede yok; "
                "olculmedi."]
    return ["  ⚪ ÖLÇÜLEMEDİ: KUTU_OKSUZ_GOVDE=OLCULEMEDI — %s ('sorun yok' demek "
            "DEGILDIR)." % s["hata"]]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    kutu = None
    if "--kutu" in argv:
        i = argv.index("--kutu")
        if i + 1 >= len(argv):
            print("KUTU_OKSUZ_GOVDE=OLCULEMEDI")
            print("OLCULEMEDI: --kutu bir yol bekliyor")
            print("HUKUM: OLCULEMEDI (rc=%d)" % RC_OLCULEMEDI)
            return RC_OLCULEMEDI
        kutu = argv[i + 1]
    s = olc(kutu)
    for satir in cikti_satirlari(s):
        print(satir)
    return HAL_RC[s["hal"]]


if __name__ == "__main__":
    sys.exit(main())
