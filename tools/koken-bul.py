#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""koken-bul.py — "BU URUNUN KOKENI NE?" sorusuna ANINDA cevap + kokeni EKSIK kayitlarin SAYIMI.

NEDEN VAR (K152, 17 Agu 2026 — Okan hukmu):
HocA "628 lazer-tarama urununde tasarimci bos" diye bulgu birakti; olculdu: 822 urun public
katalogda `lisans` objesi TASIMIYOR. Mimar bunu SATILABILIRLIK sorusu sandi. 🔴 OKAN HUKMU
SORUYU KAPATTI: "sitede bulunan TUM urunler satilabilir; SAKIN urun SILME; yapilacak sey
yalnizca EKSIK LINKLERI TAMAMLAMA — public'e link/ad KESINLIKLE YASAK, yalniz bizde intern
kayitli olacak ve ben istedigimde HEMEN bulunacak."

Yani bu aracin ekseni lisans/satilabilirlik DEGIL: **IC KOKEN KAYDININ TAMLIGI ve ERISIM
SURESI**. "Hemen bulunacak" bir niyet degil, KOSULAN BIR KOMUT olmalidir — `--bul` o komuttur.

🔴 GIZLILIK, ARACIN OMURGASI (CLAUDE.md: tedarikci/tasarimci/uyelik adi hicbir PUBLIC yerde):
  * `--bul` kipi kokeni EKRANA basar (tek urun, insan sorusu) ve ciktinin GIZLI oldugunu
    her seferinde yazar. Hicbir dosyaya YAZMAZ.
  * `--eksik` (rapor) kipi YALNIZ SAYI basar. `kaynak` degeri ancak BILINEN PLATFORM
    beyaz listesindeyse yazilir; degilse `TEDARIKCI(ad gizli)` diye maskelenir. Urun ID'si,
    baslik, URL, tasarimci, uyelik ADI rapora ASLA girmez -> commit mesajina/DEVAM.md'ye
    yapistirilabilir cikti uretir.
  * Hicbir kip veri YAZMAZ (backfill MaCiT duzlemidir; bu arac GORUR, DUZELTMEZ).

TAMLIK KURALI (olculmus siniflardan turer, tekil yama DEGIL — [[tekil-yama-sinifi-kapatmaz]]):
Bir kayit IZLENEBILIR sayilir ancak sunlardan BIRI varsa:
  (1) `link` DOLU                                   -> kaynak sayfasi geri bulunabilir
  (2) `kaynak` DOLU **ve** (`tur` DOLU ya da BEDEL alani var)
                                                    -> platform-disi alim yolu izlenebilir
      (olculdu: 948 tedarikci kaydinda URL YOK ama `kaynak`+`alis_fiyati` VAR — bunlar
       EKSIK DEGIL, cunku pazar yerinden gelmediler; URL beklemek yanlis-pozitif olurdu)
  (3) KENDI URETIMIMIZ: `parametrik` True · `tur` ozgun-* · `kaynak` pruvo-jenerator/ozgun/okan
Aksi halde EKSIK ve SEBEP KOVASINA dusar (asagidaki SEBEP_* sabitleri).

CIKIS KODU: 0 = eksik YOK · 1 = eksik VAR (bugun KIRMIZI — dogru davranis, MaCiT backfill'i
dusurur) · 2 = OLCULEMEDI (dosya okunamadi / kayit haritasi bos — fail-closed).

KULLANIM:
    python3 tools/koken-bul.py --bul <urun-id>        # tek urunun kokeni (GIZLI cikti)
    python3 tools/koken-bul.py --bul "kapi kolu"      # baslikta arar, id bulur
    python3 tools/koken-bul.py --eksik                # YALNIZ SAYI (paylasilabilir)
    python3 tools/koken-bul.py --kendini-test         # agsiz oz-denetim + mutasyon
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("PRUVO_ROOT") or os.path.dirname(HERE)
URUNLER = os.environ.get("PRUVO_URUNLER_JSON") or os.path.join(ROOT, "urunler.json")
KAYNAK = os.environ.get("PRUVO_KAYNAKLAR_JSON") or os.path.join(ROOT, ".urun-kaynaklari.json")

# ─────────────────────────────────────────────────────────────── sebep kovalari
SEBEP_KAYIT_YOK = "KAYIT_YOK"                  # public urun, gizli kayit HIC yok (yetim duzlemi)
SEBEP_KAYIT_DIZGE = "KAYIT_DIZGE"              # kayit ciplak dizge -> alanla sorgulanamaz
SEBEP_LINKSIZ_PLATFORM = "LINKSIZ_PLATFORM"    # pazar yeri kaydi ama link BOS -> DOLDURULABILIR
SEBEP_KOKEN_YOK = "KOKEN_YOK"                  # ne kaynak ne link ne beyan -> ELLE bakilacak

#: 🔴 BEYAZ LISTE — rapora YAZILABILIR kaynak adlari. Bunlar PLATFORM/host adidir (public
#: yuzeyde gecmesi CLAUDE.md'ce serbest). Listede OLMAYAN her `kaynak` degeri tedarikci
#: adi olabilir -> maskelenir. Liste GENISLETILIRKEN kural: "bu ad zaten alan adi olarak
#: public mi?" Hayirsa EKLENMEZ.
PLATFORM_ADLARI = ("cults3d", "cgtrader", "3dexport", "printables", "makerworld",
                   "thingiverse", "myminifactory", "pruvo-jenerator")
MASKE = "TEDARIKCI(ad gizli)"

#: bedel alanlari — "para el degisti" izinin ALAN ADLARI (deger BASILMAZ, yalniz varligi olculur)
BEDEL_ALANLARI = ("eur", "usd", "usd_liste", "usd_indirimli", "alis_fiyati")

#: kendi uretimimiz beyani
IC_URETIM_TUR = ("ozgun-tasarim", "ozgun-model-okan")
IC_URETIM_KAYNAK = ("pruvo-jenerator", "ozgun", "okan")

#: `--bul` ciktisinda gosterilecek alanlar (sirali). Gizli olanlar da BURADA gosterilir —
#: kip zaten "Okan sordu, ekrana bas" kipidir; rapor kipiyle KARISTIRILMAZ.
BUL_ALANLARI = ("kaynak", "tur", "alt_tur", "link", "tasarimci", "uyelik", "lisans",
                "not", "itemid", "kaynak_id", "uploader_id", "baski", "kaynak_baski_notu")


class Olculemedi(Exception):
    """fail-closed: olcum yapilamadi (yesil SAYILMAZ)."""


# ─────────────────────────────────────────────────────────────── saf yuklemler
def _s(x):
    """Alani karsilastirilabilir dizgeye cevirir (None/sayi/dict hepsi karsilanir)."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()


def bedel_var(kayit):
    if any(kayit.get(a) is not None for a in BEDEL_ALANLARI):
        return True
    # `_fiyat` suffix'i tedarikci-ozel alan adlarini gizli tutarken bedeli sayar
    return any(k.endswith("_fiyat") for k in kayit if kayit[k] is not None)


def ic_uretim(kayit, urun=None):
    if urun is not None and bool(urun.get("parametrik")):
        return True
    if _s(kayit.get("tur")).lower() in IC_URETIM_TUR:
        return True
    k = _s(kayit.get("kaynak")).lower()
    return any(k.startswith(x) or ("/" + x) in k or (": " + x) in k for x in IC_URETIM_KAYNAK)


def platform_mi(kaynak):
    """`kaynak` degeri BILINEN bir pazar yeri mi? (rapor maskesi + LINKSIZ_PLATFORM kovasi)"""
    k = _s(kaynak).lower()
    return any(p in k for p in PLATFORM_ADLARI)


def maskele(kaynak):
    """Rapora yazilabilir ad: platform ise kendisi, degilse MASKE. 🔴 Bos degeri de
    maskelemez ('KAYNAK_BOS' bilgisi sizinti degildir, ADIN KENDISI sizintidir)."""
    k = _s(kaynak)
    if not k:
        return "KAYNAK_BOS"
    if not platform_mi(k):
        return MASKE
    for p in PLATFORM_ADLARI:                       # yalniz platform JETONU yazilir,
        if p in k.lower():                          # "cults3d/<tedarikci>" TAM HALI DEGIL
            return p
    return MASKE


def izlenebilir(kayit, urun=None):
    """(True, "") ya da (False, SEBEP_*). Tamlik kurali docstring'de gerekcelendi."""
    if kayit is None:
        return False, SEBEP_KAYIT_YOK
    if not isinstance(kayit, dict):
        return False, SEBEP_KAYIT_DIZGE
    if _s(kayit.get("link")):
        return True, ""
    if ic_uretim(kayit, urun):
        return True, ""
    kaynak = _s(kayit.get("kaynak"))
    if kaynak:
        if platform_mi(kaynak):
            # pazar yerinden geldi ama URL yok -> DOLDURULABILIR eksik (asil is bu)
            return False, SEBEP_LINKSIZ_PLATFORM
        if _s(kayit.get("tur")) or bedel_var(kayit):
            return True, ""                          # platform-disi alim yolu izlenebilir
        return False, SEBEP_KOKEN_YOK
    return False, SEBEP_KOKEN_YOK


# ─────────────────────────────────────────────────────────────── okuma
def _oku(yol, bekle_tip):
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        raise Olculemedi("%s okunamadi (%s)" % (os.path.basename(yol), type(e).__name__))
    if not isinstance(veri, bekle_tip) or not veri:
        raise Olculemedi("%s beklenen sekilde degil ya da BOS" % os.path.basename(yol))
    return veri


def yukle(urunler_yolu=None, kaynak_yolu=None):
    urunler = _oku(urunler_yolu or URUNLER, list)
    kayitlar = _oku(kaynak_yolu or KAYNAK, dict)
    return urunler, kayitlar


# ─────────────────────────────────────────────────────────────── rapor (YALNIZ SAYI)
def eksik_olc(urunler, kayitlar):
    """(satirlar, eksik_toplam) — satirlarda ID/baslik/URL/ad YOKTUR."""
    kovalar = {}
    uyari_kaynak_bos_linkli = 0
    izlenen = 0
    for urun in urunler:
        uid = _s(urun.get("id"))
        if not uid:
            continue
        kayit = kayitlar.get(uid)
        ok, sebep = izlenebilir(kayit, urun)
        if ok:
            izlenen += 1
            if isinstance(kayit, dict) and not _s(kayit.get("kaynak")) and _s(kayit.get("link")):
                uyari_kaynak_bos_linkli += 1
            continue
        anahtar = "%s | %s" % (sebep, maskele((kayit or {}).get("kaynak")
                                              if isinstance(kayit, dict) else ""))
        kovalar[anahtar] = kovalar.get(anahtar, 0) + 1

    eksik = sum(kovalar.values())
    satirlar = ["KOKEN IZLENEBILIRLIGI — YALNIZ SAYI (ad/ID/URL BASILMAZ)",
                "PUBLIK_URUN=%d" % sum(1 for u in urunler if _s(u.get("id"))),
                "IZLENEBILIR=%d" % izlenen,
                "EKSIK=%d" % eksik]
    for k in sorted(kovalar, key=lambda x: (-kovalar[x], x)):
        satirlar.append("  %s = %d" % (k, kovalar[k]))
    satirlar.append("UYARI_KAYNAK_ALANI_BOS_AMA_LINK_VAR=%d  (eksik DEGIL; link'ten "
                    "doldurulabilir)" % uyari_kaynak_bos_linkli)
    satirlar.append("HUKUM=%s" % ("TEMIZ" if eksik == 0 else "EKSIK_VAR"))
    return satirlar, eksik


def defter_olc(kayitlar):
    """DEFTER ekseni — gizli kayit haritasinin TAMAMI (public urun evreninden BAGIMSIZ).

    🔴 NEDEN AYRI BASILIR: onarim DEFTER uzerinde calisir, site PUBLIK urun uzerinde. Ayni
    kova iki eksende AYRI sayi verir (olculdu: linksiz-platform defterde 88, publikte 44 —
    fark, canli public urunu OLMAYAN defter kayitlari). Iki sayiyi tek satirda karsilastirmak
    "celiski" gorunumu uretir; birim AYRIDIR ([[hukum-yanlis-birimde]]).
    🔴 Bu eksen `parametrik` bayragini GOREMEZ (o alan public urunde durur) — sari seri
    kayitlari burada KOKEN_YOK'a dusebilir; publik eksende dusMEZ. Eksenlerin ayri durmasinin
    sebebi tam olarak budur."""
    dizge = sum(1 for v in kayitlar.values() if not isinstance(v, dict))
    linksiz_platform = kokensiz = 0
    for v in kayitlar.values():
        if not isinstance(v, dict):
            continue
        _ok, sebep = izlenebilir(v)
        if sebep == SEBEP_LINKSIZ_PLATFORM:
            linksiz_platform += 1
        elif sebep == SEBEP_KOKEN_YOK:
            kokensiz += 1
    return ["--- DEFTER EKSENI (BAGIMSIZ BIRIM — publik eksenle KARSILASTIRILMAZ) ---",
            "KAYIT=%d" % len(kayitlar),
            "DEFTER_LINKSIZ_PLATFORM=%d" % linksiz_platform,
            "DEFTER_DIZGE=%d" % dizge,
            "DEFTER_KOKEN_YOK=%d  (parametrik bayragi bu eksende GORUNMEZ)" % kokensiz]


# ─────────────────────────────────────────────────────────────── tek urun (GIZLI cikti)
def id_ara(urunler, sorgu):
    """Tam ID eslesmezse baslikta ARAR -> aday ID listesi (en cok 10)."""
    q = _s(sorgu).lower()
    idler = [_s(u.get("id")) for u in urunler if _s(u.get("id"))]
    if q in [i.lower() for i in idler]:
        return [i for i in idler if i.lower() == q]
    adaylar = [_s(u.get("id")) for u in urunler
               if q and q in _s(u.get("baslik")).lower()]
    return adaylar[:10]


def bul_satirlari(urun_id, urun, kayit):
    """Tek urunun koken dokumu. 🔴 Bu cikti GIZLIDIR (ekran icin)."""
    out = ["🔴 GIZLI CIKTI — paylasma/commit'leme (tedarikci/tasarimci/uyelik bilgisi icerir)",
           "urun: %s" % urun_id,
           "baslik: %s" % _s((urun or {}).get("baslik"))]
    if kayit is None:
        out.append("KAYIT YOK — bu urunun gizli koken kaydi HIC yok (yetim).")
        return out
    if not isinstance(kayit, dict):
        out.append("KAYIT DIZGE (alanli degil): %s" % _s(kayit))
        return out
    for alan in BUL_ALANLARI:
        if alan in kayit and _s(kayit[alan]):
            deger = kayit[alan]
            if isinstance(deger, (dict, list)):
                deger = json.dumps(deger, ensure_ascii=False)
            out.append("%-18s: %s" % (alan, deger))
    baska = [k for k in sorted(kayit) if k not in BUL_ALANLARI]
    if baska:
        out.append("(diger alanlar: %s)" % ", ".join(baska))
    ok, sebep = izlenebilir(kayit, urun)
    out.append("IZLENEBILIR=%s%s" % ("EVET" if ok else "HAYIR",
                                     "" if ok else " (%s)" % sebep))
    return out


# ─────────────────────────────────────────────────────────────── oz-denetim + mutasyon
def _fx():
    """Sentetik fikstur — GERCEK cikti sekliyle ayni, degerler UYDURMA (.example TLD)."""
    urunler = [
        {"id": "u-link", "baslik": "linkli urun"},
        {"id": "u-tedarikci", "baslik": "tedarikci alimi"},
        {"id": "u-ozgun", "baslik": "kendi tasarimimiz"},
        {"id": "u-parametrik", "baslik": "sari seri", "parametrik": True},
        {"id": "u-linksiz-platform", "baslik": "pazar yeri, link yok"},
        # 🔴 MASKE EKSENI BU SATIRLA OLCULEBILIR OLUR: kaynagi TEDARIKCI ADI olan ve
        # izlenebilir OLMAYAN bir kayit olmadan `--eksik` raporu maskeye HIC ugramaz ve
        # M1 (maskesiz) mutanti KOR kalir ([[fikstur-degeri-mutasyon-koru]]).
        {"id": "u-tedarikci-koksuz", "baslik": "tedarikci ama beyan yok"},
        {"id": "u-kokensiz", "baslik": "hicbir koken yok"},
        {"id": "u-dizge", "baslik": "kayit dizge"},
        {"id": "u-kayitsiz", "baslik": "kaydi olmayan"},
        {"id": "u-kaynaksiz-linkli", "baslik": "link var kaynak bos"},
    ]
    kayitlar = {
        "u-link": {"kaynak": "cults3d/GizliTedarikci", "tur": "deal",
                   "link": "https://cults3d.example/3d-model/x", "eur": 3},
        "u-tedarikci": {"kaynak": "GizliTedarikciAdi", "tur": "satin-alma", "alis_fiyati": 12},
        "u-ozgun": {"kaynak": "ozgun", "tur": "ozgun-tasarim"},
        "u-parametrik": {"kaynak": "", "tur": ""},
        "u-linksiz-platform": {"kaynak": "cults3d/GizliTedarikci", "tur": "deal"},
        "u-tedarikci-koksuz": {"kaynak": "GizliTedarikciAdi"},
        "u-kokensiz": {"kaynak": "", "tur": "", "not": ""},
        "u-dizge": "https://bir.example/urun GizliTedarikciAdi",
        "u-kaynaksiz-linkli": {"kaynak": "", "link": "https://makerworld.example/models/1"},
    }
    return urunler, kayitlar


def kendini_test(yaz=None):
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    urunler, kayitlar = _fx()
    k = []

    # --- tamlik kurali: her sinif DOGRU kovaya dusuyor mu?
    bekle = {"u-link": (True, ""), "u-tedarikci": (True, ""), "u-ozgun": (True, ""),
             "u-parametrik": (True, ""), "u-kaynaksiz-linkli": (True, ""),
             "u-linksiz-platform": (False, SEBEP_LINKSIZ_PLATFORM),
             "u-tedarikci-koksuz": (False, SEBEP_KOKEN_YOK),
             "u-kokensiz": (False, SEBEP_KOKEN_YOK),
             "u-dizge": (False, SEBEP_KAYIT_DIZGE),
             "u-kayitsiz": (False, SEBEP_KAYIT_YOK)}
    urun_ix = {u["id"]: u for u in urunler}
    for uid, (b_ok, b_sebep) in sorted(bekle.items()):
        ok, sebep = izlenebilir(kayitlar.get(uid), urun_ix.get(uid))
        k.append(("sinif %-20s -> %s" % (uid, b_sebep or "IZLENEBILIR"),
                  (ok, sebep) == (b_ok, b_sebep)))

    satirlar, eksik = eksik_olc(urunler, kayitlar)
    metin = "\n".join(satirlar)
    k.append(("rapor: eksik sayisi 5", eksik == 5))
    k.append(("rapor: IZLENEBILIR=5", "IZLENEBILIR=5" in metin))

    # --- 🔴 SIZINTI EKSENI: rapor gizli hicbir degeri TASIMAMALI
    sizabilir = ["GizliTedarikci", "GizliTedarikciAdi", "cults3d.example",
                 "makerworld.example", "u-link", "u-dizge", "linkli urun", "sari seri"]
    for s in sizabilir:
        k.append(("sizinti YOK: %r rapora girmiyor" % s, s not in metin))
    k.append(("maske uygulandi", MASKE in metin))
    k.append(("platform adi yazilabilir", "cults3d" in metin))

    # --- IKI EKSEN AYRI BIRIM: defter sayisi publik sayisiyla AYNI OLMAK ZORUNDA DEGIL
    dmetin = "\n".join(defter_olc(kayitlar))
    k.append(("defter: KAYIT=9", "KAYIT=9" in dmetin))
    k.append(("defter: linksiz-platform=1", "DEFTER_LINKSIZ_PLATFORM=1" in dmetin))
    k.append(("defter: dizge=1", "DEFTER_DIZGE=1" in dmetin))
    k.append(("defter: kokensiz=3 (parametrik bu eksende GORUNMEZ — birim farki)",
              "DEFTER_KOKEN_YOK=3" in dmetin))
    k.append(("defter ekseni birim uyarisini TASIYOR", "KARSILASTIRILMAZ" in dmetin))
    for s in sizabilir:
        k.append(("defter ekseni sizdirmiyor: %r" % s, s not in dmetin))

    # --- maskeleme birim davranisi
    k.append(("maske: tedarikci adi maskelenir", maskele("GizliTedarikciAdi") == MASKE))
    k.append(("maske: platform jetonu (tedarikci soneki DUSER)",
              maskele("cults3d/GizliTedarikci") == "cults3d"))
    k.append(("maske: bos -> KAYNAK_BOS", maskele("") == "KAYNAK_BOS"))

    # --- --bul kipi: GIZLI cikti gercekten kokeni veriyor mu + uyari satiri var mi?
    b = "\n".join(bul_satirlari("u-link", urun_ix["u-link"], kayitlar["u-link"]))
    k.append(("bul: gizli uyarisi basiliyor", "GIZLI CIKTI" in b))
    k.append(("bul: link gosteriliyor", "cults3d.example" in b))
    k.append(("bul: kayit YOK hali soyleniyor",
              "KAYIT YOK" in "\n".join(bul_satirlari("u-kayitsiz", urun_ix["u-kayitsiz"], None))))
    k.append(("bul: dizge kayit hali soyleniyor",
              "KAYIT DIZGE" in "\n".join(
                  bul_satirlari("u-dizge", urun_ix["u-dizge"], kayitlar["u-dizge"]))))
    k.append(("id_ara: basliktan id bulur", id_ara(urunler, "sari seri") == ["u-parametrik"]))
    k.append(("id_ara: tam id eslesir", id_ara(urunler, "u-link") == ["u-link"]))
    k.append(("id_ara: bulunamayan bos doner", id_ara(urunler, "yok-boyle-bir-sey") == []))

    # --- fail-closed: bos/bozuk dosya OLCULEMEDI (yesil SAYILMAZ)
    k.append(("fail-closed: bos/bozuk dosya OLCULEMEDI", _bos_dosya_olculemedi()))

    # --- MUTASYON: kurali bozan varyantlar KIRMIZI yanmali (kontrol satiri dahil)
    mutantlar = [
        ("M1 sizinti: maske kalkarsa", lambda: _mutant_maskesiz(urunler, kayitlar)),
        ("M2 linksiz platform 'temiz' sayilirsa", lambda: _mutant_linksiz_temiz()),
        ("M3 dizge kayit 'temiz' sayilirsa", lambda: _mutant_dizge_temiz()),
        ("M4 kaynaksiz+linksiz 'temiz' sayilirsa", lambda: _mutant_kokensiz_temiz()),
        ("M5 KONTROL: kural aynen -> DEGISMEZ", lambda: _mutant_kontrol(urunler, kayitlar)),
    ]
    for ad, fn in mutantlar:
        k.append((ad, fn()))

    gecen = sum(1 for _a, ok in k if ok)
    for ad, ok in k:
        yaz("  %-4s %s" % ("ok" if ok else "HATA", ad))
    return gecen, len(k)


def _bos_dosya_olculemedi():
    """BOS/bozuk girdi gercekten Olculemedi mi? (fail-closed ekseni)"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        y = os.path.join(d, "bos.json")
        with open(y, "w", encoding="utf-8") as f:
            f.write("[]")
        try:
            _oku(y, list)
            return False
        except Olculemedi:
            pass
        y2 = os.path.join(d, "bozuk.json")
        with open(y2, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        try:
            _oku(y2, dict)
            return False
        except Olculemedi:
            return True


def _mutant_maskesiz(urunler, kayitlar):
    """Maske kalkarsa rapora tedarikci adi girer -> mutant OLDU (True = yakalandi)."""
    kovalar = {}
    for u in urunler:
        kayit = kayitlar.get(_s(u.get("id")))
        ok, sebep = izlenebilir(kayit, u)
        if ok:
            continue
        ham = _s(kayit.get("kaynak")) if isinstance(kayit, dict) else ""
        kovalar["%s | %s" % (sebep, ham or "KAYNAK_BOS")] = 1
    return "GizliTedarikci" in "\n".join(kovalar)


def _mutant_linksiz_temiz():
    kayit = {"kaynak": "cults3d/GizliTedarikci", "tur": "deal"}
    return izlenebilir(kayit)[1] == SEBEP_LINKSIZ_PLATFORM


def _mutant_dizge_temiz():
    return izlenebilir("ciplak dizge")[1] == SEBEP_KAYIT_DIZGE


def _mutant_kokensiz_temiz():
    return izlenebilir({"kaynak": "", "tur": ""})[1] == SEBEP_KOKEN_YOK


def _mutant_kontrol(urunler, kayitlar):
    """KONTROL: kural degismedi -> sayi AYNI kalmali (fikstur degeri mutasyonu kor etmesin)."""
    _s1, e1 = eksik_olc(urunler, kayitlar)
    _s2, e2 = eksik_olc(urunler, kayitlar)
    return e1 == e2 == 5


# ─────────────────────────────────────────────────────────────── CLI
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Urun kokeni: ANINDA BUL (gizli cikti) ya da EKSIKLERI SAY (yalniz sayi). "
                    "Hicbir kip veri YAZMAZ.")
    ap.add_argument("--bul", metavar="ID_YA_DA_BASLIK",
                    help="tek urunun koken dokumu (🔴 GIZLI cikti — paylasma)")
    ap.add_argument("--eksik", action="store_true",
                    help="kokeni eksik kayitlarin SAYIMI (ad/ID/URL basmaz)")
    ap.add_argument("--kendini-test", action="store_true", help="agsiz oz-denetim + mutasyon")
    a = ap.parse_args(argv)

    if a.kendini_test:
        gecen, toplam = kendini_test()
        print("")
        print("OZ-DENETIM %s — GECEN=%d/%d"
              % ("GECTI" if gecen == toplam else "BASARISIZ", gecen, toplam))
        return 0 if gecen == toplam else 1

    if not a.bul and not a.eksik:
        print("OLCULEMEDI — kip secilmedi (--bul <id> | --eksik | --kendini-test)")
        return 2

    try:
        urunler, kayitlar = yukle()
    except Olculemedi as e:
        print("OLCULEMEDI — %s" % e)
        return 2

    if a.bul:
        adaylar = id_ara(urunler, a.bul)
        if not adaylar:
            print("BULUNAMADI — ne ID ne baslik eslesti: %r" % a.bul)
            return 1
        urun_ix = {_s(u.get("id")): u for u in urunler}
        for uid in adaylar:
            print("")
            for satir in bul_satirlari(uid, urun_ix.get(uid), kayitlar.get(uid)):
                print(satir)
        if len(adaylar) > 1:
            print("")
            print("(%d aday listelendi — daha dar sorgu ver)" % len(adaylar))
        return 0

    satirlar, eksik = eksik_olc(urunler, kayitlar)
    for satir in satirlar + defter_olc(kayitlar):
        print(satir)
    return 0 if eksik == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
