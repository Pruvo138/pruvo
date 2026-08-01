#!/usr/bin/env python3
"""parti-kontrol.py — toplu urun ekleme PARTISININ kabul testi.

PARTI = working-tree urunler.json'da olup `git show HEAD:urunler.json` ciktisinda
OLMAYAN id'ler (yeni stage'lenmis urunler). Bu arac SADECE partiyi denetler;
HEAD'de zaten var olan urunlere dokunmaz (onlar urunler-guard.py'nin isi).

Her yeni urun icin kontroller:
  1. id kebab-case ve bos degil
  2. baslik bos degil
  3. kategori gecerli kategori listesinde
  4. marka alani liste tipinde
  5. gorseller >= 1 eleman ve hepsi https://media.pruvo3d.com/ ile baslar
     (DAR ISTISNA — bkz. _gorselsiz_muaf: urun kaydinda ACIKCA `"gorselsiz": true`
      beyani VARSA **ve** urun hazir ticari mal ise (`tur == "fiziksel"`), gorsel HIC
      olmayabilir. Bayraksiz gorselsiz urun ve baski/ozel uretim urunu KIRMIZI kalir;
      gorsel VARSA media.pruvo3d.com oneki AYNEN aranir. Istisna uygulanan satirlar
      sessiz gecmez: "gorselsiz kabul edilen: N (id...)" satiriyla basilir.)
  6. aciklamada "3d bask" gecmez (buyuk/kucuk harf duyarsiz)
  7. fiyat: parametrik=true ise BOS; degilse "<sayi> TL" biciminde
  8. aciklamada "mm" iceren bir olcu ifadesi (ISTISNA: .urun-kaynaklari.json'da
     tur=="satin-alma" olan urunlerde olcu aranmaz)
  9. lisans alani VARSA dict ve icindeki "tur" bos degil

MEVCUT-URUN-DEGISIKLIGI KIPI (backfill): HEAD'de zaten var olan urunlerin alanlari
degistiginde (or. gorsel backfill) yapisal dogrulama yapar — eskiden bu tamamen
korlemesine YESIL'di ("parti yok: working tree = HEAD"). Kontroller:
  - mevcut id kayboldu (urun silinmis) -> RED (default + strict)
  - degisen mevcut urunlerde yeni gorseller[] gecerli https://media.pruvo3d.com/... mi
    (ayni DAR ISTISNA burada da gecerli: `gorselsiz` bayrakli FIZIKSEL urunde gorsel
     listesi bosalabilir. Bayragin KENDISI backfill'de eklenemez — `gorseller` disi
     her alan degisikligi zaten RED; yani bayrak yalniz urun EKLENIRKEN beyan edilir.)
  - backfill-disi alan (fiyat/baslik/kategori...) sessizce degistiyse -> RED
  - --backfill (strict): urun SAYISI sabit + hic yeni id belirmemeli (backfill
    urun EKLEMEZ/SILMEZ, sadece alan gunceller)

Bulgu varsa her biri "SORUN <id>: <aciklama>" satiriyla yazilir, cikis 1.
Temizse "parti temiz: N yeni urun, M mevcut urun degisikligi kontrol edildi", cikis 0.
Yeni urun yok ve mevcut urun degismemisse "parti yok: working tree = HEAD", cikis 0.

--test: gercek dosyalara dokunmadan her kontrolun yakalama+gecme yolunu sinar.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAKLAR = os.path.join(ROOT, ".urun-kaynaklari.json")

def _gecerli_kategoriler():
    """Gecerli kategoriler: index.html + tools/build.py'den PROGRAMATIK okunur.

    Liste burada TUTULMAZ (ikinci kopya = drift kaynagi); tools/kategori-kapisi.py
    iki kaynagi karsilastirip birlesimi dondurur (nav + GIZLI "Jeneratör").
    """
    yol = os.path.join(ROOT, "tools", "kategori-kapisi.py")
    spec = importlib.util.spec_from_file_location("kategori_kapisi", yol)
    if spec is None or spec.loader is None:
        sys.exit("HATA: tools/kategori-kapisi.py yuklenemedi: " + yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.gecerli_kategoriler())


# ASCII TOLERANSI KALDIRILDI (yasanmis sessiz hata): eskiden "Bahce"/"Jenerator" da
# gecerli sayiliyordu; boyle bir urun katalogda DURUR ama index.html cipi
# `p.kategori === activeCat` ile eslesmedigi icin kategoriden GORUNMEZ. Artik yalnizca
# kanonik ad gecer; ASCII'ye dusme kaynaginda (thing-codex.py) normalize edilir.
KATEGORILER = _gecerli_kategoriler()


def _arama_modulu():
    """tools/arama.py — TICARI SINIFIN (`tur`) TEK KAYNAGI.

    "fiziksel" dizesini burada TEKRAR YAZMIYORUZ (ikiz tanim sessizce ayrisir):
    sinif karari arama.tur_kanonik'ten gelir; ayni fonksiyonu build.py/d1-sync.py da
    kullanir. Yuklenemezse FAIL-CLOSED cikilir — sinif belirlenemeden gorsel muafiyeti
    verilemez (sessizce "muaf degil" demek de yanlis olurdu: kapi sessizce ayrisirdi).
    """
    yol = os.path.join(ROOT, "tools", "arama.py")
    spec = importlib.util.spec_from_file_location("arama_parti_kontrol", yol)
    if spec is None or spec.loader is None:
        sys.exit("HATA: tools/arama.py yuklenemedi: " + yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "tur_kanonik"):
        sys.exit("HATA: tools/arama.py'de tur_kanonik yok: " + yol)
    return mod


_ARAMA = _arama_modulu()

MEDYA_ONEK = "https://media.pruvo3d.com/"

# Gorsel zorunlulugundan DAR muafiyet beyani (urun kaydinda ACIK alan).
GORSELSIZ_BAYRAK = "gorselsiz"

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FIYAT_RE = re.compile(r"^\d[\d.,]* TL$")
# olcu ifadesi: OTOMATIK URETILEN CAPALI ifadeye baglan (denetim-kapisi._OLCU_RE ile AYNI karar).
# Eski gevsek desen (r"\d[\d\s.,×xX*+-]*mm\b") aciklamadaki KISMI spec-mm degerini ("M32×3.5,
# ~31 mm") gercek olcu satiriyla karistirip olcusuz urunu "olculu" sayiyordu (yanlis-negatif).
# Capa ifadesine ("Yaklasik dis olculer" + eski ASCII yazim) baglanip AYNI SATIRDA araya giren
# etiket/parantez metnine ([^\n]*?) izin vererek ilk "<sayi> … mm" tokenina ilerle -> etiketli/
# parantezli biciM ("... : taban 137 × 135 × 70 mm.", "(15 cm boyda): 113 × ...") de yakalanir;
# placeholder ("… : yok." / "- × - mm.") DIJIT tasimadigi icin olcusuz kalir (dogru).
_OLCU_RE = re.compile(
    r"Yakla[şs][ıi]k\s+d[ıi][şs]\s+[öo]l[çc][üu]ler[^\n]*?\d[\d\s.,×xX*+-]*mm\b", re.UNICODE)


def _git(*args):
    """git -C ROOT <args> -> (rc, stdout_bytes). Hata yutulur."""
    try:
        p = subprocess.run(["git", "-C", ROOT, *args], capture_output=True)
        return p.returncode, p.stdout
    except Exception:
        return 1, b""


def _head_urunler():
    """HEAD:urunler.json'daki tam urun listesi; okunamazsa None (parti belirlenemez)."""
    rc, out = _git("show", "HEAD:urunler.json")
    if rc != 0:
        return None
    try:
        urunler = json.loads(out.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return urunler if isinstance(urunler, list) else None


def _ids_kumesi(urunler):
    """Urun listesinden (dict'lerden) id kumesi; None id atlanir."""
    return {
        u.get("id") for u in urunler
        if isinstance(u, dict) and u.get("id") is not None
    }


def _head_ids():
    """HEAD:urunler.json'daki id kumesi; okunamazsa None (parti belirlenemez)."""
    urunler = _head_urunler()
    if urunler is None:
        return None
    return _ids_kumesi(urunler)


def _kaynaklari_oku(path):
    """Kaynak haritasi yoksa veya bozuksa sessizce bos sozluk dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kaynaklar = json.load(f)
    except (OSError, ValueError):
        return {}
    return kaynaklar if isinstance(kaynaklar, dict) else {}


def _satin_alma_mi(kayit):
    """Kaynak kaydi tur=="satin-alma" olan bir dict ise True.

    Kayit str/dict/list bicimlerinde olabilir; SADECE dict'te "tur" anahtarina
    bakilir, diger bicimlerde olcu istisnasi UYGULANMAZ.
    """
    return isinstance(kayit, dict) and kayit.get("tur") == "satin-alma"


# Olcu, ekleme aninda ALINAMAYAN kaynaklar (indirme login/hesap/OAuth-gated) -> olcu kapisindan MUAF.
# denetim-kapisi._olcu_muaf_kaynak ile AYNI desen. Printables/Thingiverse MUAF DEGIL (olculu gelir).
_OLCU_MUAF_KAYNAK = {"makerworld", "cults3d", "myminifactory", "cgtrader"}
_OLCU_MUAF_DOMAIN = ("makerworld.com", "cults3d.com", "myminifactory.com", "cgtrader.com")


def _olcu_muaf(kayit):
    """tur==satin-alma (CGTrader) VEYA kaynak/link MakerWorld/Cults3D/MyMiniFactory/CGTrader ise True
    (bu platformlar urunu OLCUSUZ ekler; olcu siparis/indirme sonrasi alinir). str/dict karsilanir."""
    if isinstance(kayit, dict):
        if kayit.get("tur") == "satin-alma":
            return True
        if str(kayit.get("kaynak") or "").strip().lower() in _OLCU_MUAF_KAYNAK:
            return True
        link = str(kayit.get("link") or "").lower()
    elif isinstance(kayit, str):
        link = kayit.lower()
    else:
        return False
    return any(dom in link for dom in _OLCU_MUAF_DOMAIN)


# ---------------------------------------------------------------------------
# GORSEL ZORUNLULUGU — VARSAYILAN AYNEN ZORUNLU, ISTISNA DAR VE BEYANLI
#
# Okan karari (1 Agu): belirli FIZIKSEL (hazir ticari mal) satin-alma urunlerinde
# darbogaz gorsel degil urun kimligi/OEM kodu -> gorsel HIC olmayabilir. Bu kural
# BLANKET DEGIL; ucu birden saglanmadan muafiyet DOGMAZ:
#   (1) urun kaydinda ACIK beyan: "gorselsiz": true  — ORNUK CIKARIM YOK, arac
#       kendiliginden "bu fizikselse gecerim" DEMEZ; bayraksiz gorselsiz urun KIRMIZI.
#   (2) urun HAZIR TICARI MAL sinifinda: tur == "fiziksel" (arama.tur_kanonik, tek
#       kaynak). Baski/ozel uretim urununde bayrak verilse bile KIRMIZI.
#   (3) gorsel GERCEKTEN yok: alan hic yok ya da BOS LISTE. Bicimsiz deger
#       ("gorseller": "x" / null / {}) "yok" SAYILMAZ -> istisna onu ACMAZ.
# Gorsel VARSA media.pruvo3d.com onek kurali AYNEN gecerlidir; istisna yalniz
# "hic gorsel yok" halini acar, KOTU gorseli degil.
#
# TIP TUZAGI (bilerek `is True`): Python'da True == 1 ve isinstance(True, int).
# `if urun.get("gorselsiz")` yazsaydik "true" dizesi, 1, [] disi her truthy deger
# muafiyet acardi -> beyan alani sessizce "her sey" olurdu (arama.stokta_kanonik ile
# AYNI kimlik testi disiplini).
# ---------------------------------------------------------------------------

def _gorsel_yok(urun):
    """Gorsel HIC YOK hali: `gorseller` alani yok VEYA bos liste.

    Bicimsiz deger (str/dict/None/sayi) burada "yok" SAYILMAZ; oyle bir kayit
    bozuk veridir ve istisnadan yararlanamaz (mevcut "liste degil" bulgusu kalir).
    """
    if not isinstance(urun, dict):
        return False
    if "gorseller" not in urun:
        return True
    g = urun.get("gorseller")
    return isinstance(g, list) and not g


def _gorselsiz_muaf(urun):
    """ACIK beyan + FIZIKSEL sinif -> gorsel zorunlulugundan muaf mi? (dar istisna)"""
    if not isinstance(urun, dict):
        return False
    if urun.get(GORSELSIZ_BAYRAK) is not True:
        return False
    # tur_kanonik: "fiziksel" ya da "" (ozel uretim). Bos dize = baski -> muafiyet YOK.
    return bool(_ARAMA.tur_kanonik(urun))


def _muafiyet_islendi(urun):
    """Istisna bu urunde GERCEKTEN uygulandi mi (gorunurluk sayimi bundan turer)."""
    return _gorsel_yok(urun) and _gorselsiz_muaf(urun)


def _gorselsiz_bulgulari(urun):
    """`gorseller` bos/eksik/bicimsiz halinin karari — yeni-urun ve backfill
    kollarinin ORTAK tek kaynagi. Bos liste dondurmesi = istisna islendi."""
    if _muafiyet_islendi(urun):
        return []
    bulgular = []
    if urun.get(GORSELSIZ_BAYRAK) is True and _gorsel_yok(urun):
        # Bayrak var ama sinif tutmuyor: muafiyet YOK ve bu sessiz kalmasin.
        bulgular.append(
            "gorselsiz bayragi yalniz tur=='fiziksel' urunde gecerli; "
            "bu urunde gorsel ZORUNLU")
    bulgular.append("gorseller bos veya liste degil")
    return bulgular


def _denetle_urun(urun, gosterim_id, kaynaklar):
    """Tek bir yeni urun icin bulgu (aciklama) listesi dondurur."""
    bulgular = []

    # 1. id kebab-case ve bos degil
    urun_id = urun.get("id")
    if not isinstance(urun_id, str) or not _KEBAB_RE.match(urun_id):
        bulgular.append("id kebab-case degil veya bos: %r" % (urun_id,))

    # 2. baslik bos degil
    baslik = urun.get("baslik")
    if not isinstance(baslik, str) or not baslik.strip():
        bulgular.append("baslik bos")

    # 3. kategori gecerli
    kategori = urun.get("kategori")
    if kategori not in KATEGORILER:
        bulgular.append("kategori gecersiz: %r" % (kategori,))

    # 4. marka liste tipinde
    if not isinstance(urun.get("marka"), list):
        bulgular.append("marka liste tipinde degil")

    # 5. gorseller >= 1 ve hepsi media.pruvo3d.com ile baslar
    #    (DAR ISTISNA: acikca "gorselsiz": true beyan eden FIZIKSEL urunde gorsel
    #     aranmaz — karar _gorselsiz_bulgulari'nda, backfill koluyla ORTAK.)
    gorseller = urun.get("gorseller")
    if not isinstance(gorseller, list) or not gorseller:
        bulgular.extend(_gorselsiz_bulgulari(urun))
    else:
        for g in gorseller:
            if not isinstance(g, str) or not g.startswith(MEDYA_ONEK):
                bulgular.append("gorsel media.pruvo3d.com ile baslamiyor: %r" % (g,))

    # 6. aciklamada "3d bask" gecmez
    aciklama = urun.get("aciklama")
    aciklama_str = aciklama if isinstance(aciklama, str) else ""
    if "3d bask" in aciklama_str.lower():
        bulgular.append("aciklamada '3d bask' geciyor")

    # 7. fiyat kurali
    parametrik = bool(urun.get("parametrik"))
    fiyat = urun.get("fiyat", "")
    fiyat_str = fiyat if isinstance(fiyat, str) else str(fiyat)
    if parametrik:
        if fiyat_str.strip():
            bulgular.append("parametrik urunde fiyat bos degil: %r" % (fiyat,))
    else:
        if not _FIYAT_RE.match(fiyat_str):
            bulgular.append("fiyat '<sayi> TL' biciminde degil: %r" % (fiyat,))

    # 8. olcu (mm) ifadesi — olcu-muaf kaynaklarda (satin-alma + login-gated MakerWorld/
    #    Cults3D/MyMiniFactory) aranmaz; Printables/Thingiverse'te ZORUNLU.
    if not _olcu_muaf(kaynaklar.get(gosterim_id)):
        if not _OLCU_RE.search(aciklama_str):
            bulgular.append("aciklamada olcu (mm) ifadesi yok")

    # 9. lisans VARSA dict ve tur dolu
    if "lisans" in urun:
        lisans = urun.get("lisans")
        if not isinstance(lisans, dict):
            bulgular.append("lisans dict degil")
        else:
            tur = lisans.get("tur")
            if not isinstance(tur, str) or not tur.strip():
                bulgular.append("lisans.tur bos")

    return bulgular


def _yeni_urunler(urunler, head_ids):
    """(gosterim_id, urun) ciftlerinden parti; HEAD'de olmayan id'ler."""
    parti = []
    for sira, urun in enumerate(urunler):
        if not isinstance(urun, dict):
            continue
        urun_id = urun.get("id")
        if urun_id in head_ids:
            continue  # HEAD'de var -> mevcut urun, parti disi (guard'in isi)
        gosterim_id = urun_id if isinstance(urun_id, str) and urun_id else "#%d" % (sira + 1)
        parti.append((gosterim_id, urun))
    return parti


def _parti_denetle(urunler, head_ids, kaynaklar):
    """Parti bulgularini [(gosterim_id, aciklama), ...] olarak dondurur; ayrica
    (bulgular, parti_boyu). head_ids None ise parti belirlenemez -> (None, None)."""
    if head_ids is None:
        return None, None
    parti = _yeni_urunler(urunler, head_ids)
    bulgular = []
    for gosterim_id, urun in parti:
        for aciklama in _denetle_urun(urun, gosterim_id, kaynaklar):
            bulgular.append((gosterim_id, aciklama))
    return bulgular, len(parti)


# ---------------------------------------------------------------------------
# MEVCUT-URUN-DEGISIKLIGI (backfill) KIPI
# HEAD'de zaten var olan urunlerin alanlari degistiginde yapisal dogrulama.
# ---------------------------------------------------------------------------

def _urun_haritasi(urunler):
    """id -> urun dict. Sadece str+dolu id'li dict'ler alinir (son gelen kazanir)."""
    harita = {}
    for u in urunler:
        if isinstance(u, dict) and isinstance(u.get("id"), str) and u.get("id"):
            harita[u["id"]] = u
    return harita


def _mevcut_denetle(onceki, sonraki, kaynaklar=None, strict=False):
    """HEAD (onceki) -> working tree (sonraki) arasi MEVCUT urun degisikligi bulgulari.

    [(gosterim_id, aciklama), ...] dondurur (bos = temiz). Kontroller:
      - mevcut id kayboldu (urun silinmis) -> her zaman RED
      - degisen ortak urunlerde: gorseller degistiyse yeni durum gecerli
        https://media.pruvo3d.com/... olmali; degil -> RED
      - gorseller DISI alan (fiyat/baslik/kategori/marka/aciklama/lisans/...)
        degistiyse -> RED (sessiz backfill-disi degisiklik). `gorselsiz` ve `tur`
        de bu kurala TABIDIR: muafiyet bayragi backfill'de EKLENEMEZ, yalniz urun
        eklenirken beyan edilir (fail-closed).
    strict=True (--backfill): ek olarak
      - urun sayisi degistiyse -> RED
      - yeni id belirdiyse -> RED (backfill urun eklemez)
    YENI urunler (yeni-urun kipi) burada denetlenmez; onlar _parti_denetle'nin isi.
    """
    del kaynaklar  # su an kullanilmiyor; imza ileriye donuk
    bulgular = []
    o_map = _urun_haritasi(onceki)
    s_map = _urun_haritasi(sonraki)
    o_ids = set(o_map)
    s_ids = set(s_map)

    if strict and len(onceki) != len(sonraki):
        bulgular.append(("*", "urun sayisi degisti: %d -> %d" % (len(onceki), len(sonraki))))

    # mevcut id kayboldu -> silme, her zaman RED
    for kid in sorted(o_ids - s_ids):
        bulgular.append((kid, "mevcut id kayboldu (urun silinmis)"))

    # strict backfill'de yeni id EKLENEMEZ
    if strict:
        for nid in sorted(s_ids - o_ids):
            bulgular.append((nid, "backfill'de yeni id belirdi (backfill urun eklemez)"))

    # ortak id'lerde alan-bazli diff
    for uid in sorted(o_ids & s_ids):
        o = o_map[uid]
        s = s_map[uid]
        for alan in sorted(set(o) | set(s)):
            if o.get(alan) == s.get(alan):
                continue  # alan degismemis
            if alan == "gorseller":
                g = s.get("gorseller")
                if not isinstance(g, list) or not g:
                    # yeni-urun koluyla ORTAK karar (dar istisna dahil)
                    for aciklama in _gorselsiz_bulgulari(s):
                        bulgular.append((uid, aciklama))
                else:
                    for x in g:
                        if not isinstance(x, str) or not x.startswith(MEDYA_ONEK):
                            bulgular.append(
                                (uid, "gecersiz gorsel URL semasi: %r" % (x,)))
            else:
                bulgular.append(
                    (uid, "backfill-disi alan '%s' sessizce degisti: %r -> %r"
                     % (alan, o.get(alan), s.get(alan))))
    return bulgular


def _parti_muaflar(urunler, head_ids):
    """Partide gorsel muafiyeti UYGULANAN yeni urunlerin gosterim id'leri."""
    if head_ids is None:
        return []
    return [gid for gid, urun in _yeni_urunler(urunler, head_ids)
            if _muafiyet_islendi(urun)]


def _mevcut_muaflar(onceki, sonraki):
    """Backfill'de gorseller BOSALAN ve muafiyet uygulanan mevcut urun id'leri."""
    o_map = _urun_haritasi(onceki)
    s_map = _urun_haritasi(sonraki)
    return sorted(
        uid for uid in (set(o_map) & set(s_map))
        if o_map[uid].get("gorseller") != s_map[uid].get("gorseller")
        and _muafiyet_islendi(s_map[uid])
    )


# ---------------------------------------------------------------------------
# CIKTI — GORUNURLUK
# main() sadece BASAR; ne yazilacagini bu saf fonksiyon belirler ki "gorselsiz kabul
# edilen" sayaci kabul testinden GECEBILSIN. Sayac, bulgu OLSA DA OLMASA DA basilir
# (sifir da basilir): sessiz muafiyet yeni bir korluk uretir.
# ---------------------------------------------------------------------------

def _muaf_satiri(muaf_idler):
    """Muafiyet sayaci satiri — hep uretilir, bos gecilmez."""
    if muaf_idler:
        return "gorselsiz kabul edilen: %d (%s)" % (
            len(muaf_idler), ", ".join(muaf_idler))
    return "gorselsiz kabul edilen: 0"


def _rapor_satirlari(yeni_bulgular, yeni_boyut, mevcut_bulgular, degisen, silinen,
                     muaf_idler):
    """(basilacak_satirlar, cikis_kodu). Denetlenecek hicbir sey yoksa sayac basilmaz."""
    if yeni_boyut == 0 and not degisen and not silinen:
        return ["parti yok: working tree = HEAD"], 0

    satirlar = [_muaf_satiri(muaf_idler)]
    tum_bulgular = list(yeni_bulgular or []) + list(mevcut_bulgular or [])
    if tum_bulgular:
        for gosterim_id, aciklama in tum_bulgular:
            satirlar.append("SORUN %s: %s" % (gosterim_id, aciklama))
        return satirlar, 1

    satirlar.append(
        "parti temiz: %d yeni urun, %d mevcut urun degisikligi kontrol edildi"
        % (yeni_boyut, len(degisen)))
    return satirlar, 0


def _mevcut_degisenler(onceki, sonraki):
    """(degisen_ortak_id_listesi, silinen_id_kumesi) — cikti mesaji icin sayim."""
    o_map = _urun_haritasi(onceki)
    s_map = _urun_haritasi(sonraki)
    degisen = [uid for uid in (set(o_map) & set(s_map)) if o_map[uid] != s_map[uid]]
    silinen = set(o_map) - set(s_map)
    return degisen, silinen


# ---------------------------------------------------------------------------
# --test: her kontrolun yakalama (fail) + gecme (pass) yolunu bellek icinde sina
# ---------------------------------------------------------------------------

def _gecerli_urun():
    """Tum kontrollerden gecen ornek urun (sablon)."""
    return {
        "id": "ornek-parca-braketi",
        "kategori": "Otomobil",
        "marka": ["Audi"],
        "baslik": "Ornek Parca Braketi",
        "aciklama": "Dayanikli braket. Yaklasik dis olculer: 40 x 25 x 10 mm.",
        "fiyat": "850 TL",
        "gorseller": ["https://media.pruvo3d.com/urunler/ornek-1.jpg"],
    }


def _oz_sinama():
    kaynaklar = {}  # varsayilan: bos kaynak haritasi

    def bulgu(urun, kaynaklar=kaynaklar, gid=None):
        u = dict(_gecerli_urun())
        u.update(urun)
        gosterim = gid if gid is not None else u.get("id") or "#1"
        return _denetle_urun(u, gosterim, kaynaklar)

    def yakalar(desen, **degisiklik):
        """degisiklik uygulaninca 'desen' iceren bir bulgu cikmali."""
        return any(desen in b for b in bulgu(degisiklik))

    def temiz(**degisiklik):
        """degisiklik uygulaninca hic bulgu cikmamali."""
        return not bulgu(degisiklik)

    kontroller = [
        # sablonun kendisi temiz olmali
        ("sablon temiz", temiz()),

        # 1. id
        ("id yakala (bos)", yakalar("id kebab-case", id="")),
        ("id yakala (bosluk)", yakalar("id kebab-case", id="Ornek Parca")),
        ("id yakala (buyuk harf)", yakalar("id kebab-case", id="Ornek-Parca")),
        ("id yakala (bitis tire)", yakalar("id kebab-case", id="ornek-parca-")),
        ("id gec", temiz(id="ornek-parca-2")),

        # 2. baslik
        ("baslik yakala (bos)", yakalar("baslik bos", baslik="")),
        ("baslik yakala (bosluk)", yakalar("baslik bos", baslik="   ")),
        ("baslik gec", temiz(baslik="Bir Baslik")),

        # 3. kategori
        ("kategori yakala", yakalar("kategori gecersiz", kategori="Uzay")),
        ("kategori yakala (yok)", yakalar("kategori gecersiz", kategori=None)),
        ("kategori gec", temiz(kategori="Tamirat")),

        # 4. marka
        ("marka yakala (str)", yakalar("marka liste", marka="Audi")),
        ("marka yakala (yok)", yakalar("marka liste", marka=None)),
        ("marka gec (bos liste)", temiz(marka=[])),

        # 5. gorseller
        ("gorsel yakala (bos)", yakalar("gorseller bos", gorseller=[])),
        ("gorsel yakala (liste degil)", yakalar("gorseller bos", gorseller="x")),
        ("gorsel yakala (yanlis host)",
         yakalar("baslamiyor", gorseller=["https://example.com/x.jpg"])),
        ("gorsel gec (coklu)", temiz(gorseller=[
            "https://media.pruvo3d.com/urunler/a-1.jpg",
            "https://media.pruvo3d.com/urunler/a-2.jpg",
        ])),

        # 5b. GORSELSIZ DAR ISTISNA — varsayilan ZORUNLULUK korunuyor mu?
        # 🔴 ONCE-KIRMIZI capalari: bayrak YOKSA gorselsiz urun (fiziksel olsun ya da
        # olmasin) KIRMIZI kalir. Istisna varsayilani ACMIYORSA bu ikisi yesil kalir.
        ("gorselsiz bayraksiz KIRMIZI (fiziksel)",
         yakalar("gorseller bos", tur="fiziksel", gorseller=[])),
        ("gorselsiz bayraksiz KIRMIZI (tursuz/baski)",
         yakalar("gorseller bos", gorseller=[])),
        ("gorselsiz bayraksiz KIRMIZI (alan hic yok)",
         any("gorseller bos" in b for b in _denetle_urun(
             {"id": "x", "kategori": "Marin", "marka": [], "baslik": "X",
              "aciklama": "Yaklasik dis olculer: 1 x 1 x 1 mm.", "fiyat": "850 TL",
              "tur": "fiziksel"}, "x", {}))),

        # KABUL: bayrak + fiziksel + gorsel yok -> gecer (yeni davranis)
        ("bayrakli fiziksel gorselsiz GECER",
         temiz(tur="fiziksel", gorselsiz=True, gorseller=[])),
        ("bayrakli fiziksel gorsel alani YOK GECER",
         not _denetle_urun(
             {"id": "x", "kategori": "Marin", "marka": [], "baslik": "X",
              "aciklama": "Yaklasik dis olculer: 1 x 1 x 1 mm.", "fiyat": "850 TL",
              "tur": "fiziksel", "gorselsiz": True}, "x", {})),

        # RED: bayrak BASKI (ozel uretim) urununde muafiyet DOGURMAZ
        ("bayrakli baski gorselsiz KIRMIZI",
         yakalar("gorseller bos", gorselsiz=True, gorseller=[])),
        ("bayrakli baski gorselsiz gerekce basar",
         yakalar("yalniz tur=='fiziksel'", gorselsiz=True, gorseller=[])),
        ("bayrakli parametrik gorselsiz KIRMIZI",
         yakalar("gorseller bos", parametrik=True, fiyat="", gorselsiz=True,
                 gorseller=[])),

        # RED: `tur` FAIL-CLOSED — yalniz tam "fiziksel" dizesi sinif acar
        ("tur 'Fiziksel' KIRMIZI", yakalar(
            "gorseller bos", tur="Fiziksel", gorselsiz=True, gorseller=[])),
        ("tur ' fiziksel' KIRMIZI", yakalar(
            "gorseller bos", tur=" fiziksel", gorselsiz=True, gorseller=[])),
        ("tur 'fiziksel-degil' KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel-degil", gorselsiz=True, gorseller=[])),

        # RED: bayrak FAIL-CLOSED — yalniz gercek boolean True beyandir
        ("bayrak 'true' dizesi KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz="true", gorseller=[])),
        ("bayrak 1 (int) KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz=1, gorseller=[])),
        ("bayrak 'evet' KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz="evet", gorseller=[])),
        ("bayrak False KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz=False, gorseller=[])),

        # RED: istisna yalniz "hic gorsel yok" halini acar — BOZUK gorsel alanini DEGIL
        ("bayrakli fiziksel gorseller 'x' KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz=True, gorseller="x")),
        ("bayrakli fiziksel gorseller None KIRMIZI", yakalar(
            "gorseller bos", tur="fiziksel", gorselsiz=True, gorseller=None)),

        # RED: onek kurali istisnadan ETKILENMEZ (gorsel VARSA aynen aranir)
        ("bayrakli fiziksel yanlis onek KIRMIZI", yakalar(
            "baslamiyor", tur="fiziksel", gorselsiz=True,
            gorseller=["https://example.com/x.jpg"])),
        ("bayrakli fiziksel http onek KIRMIZI", yakalar(
            "baslamiyor", tur="fiziksel", gorselsiz=True,
            gorseller=["http://media.pruvo3d.com/urunler/a-1.jpg"])),
        ("bayrakli fiziksel dogru onek GECER", temiz(
            tur="fiziksel", gorselsiz=True,
            gorseller=["https://media.pruvo3d.com/urunler/a-1.jpg"])),

        # 6. 3d bask (aciklamalar CAPALI olcu ifadesi tasir ki olcu kapisina takilmasinlar;
        #    boylece bu kontroller yalniz "3d bask" bulgusunu izole eder)
        ("3dbask yakala", yakalar(
            "3d bask", aciklama="Bu urun 3D baski ile uretilir. Yaklasik dis olculer: 10 x 8 x 5 mm.")),
        ("3dbask yakala (kucuk)", yakalar(
            "3d bask", aciklama="3d baski parcasi. Yaklasik dis olculer: 10 x 8 x 5 mm.")),
        ("3dbask gec", temiz(aciklama="Ozel uretim parca. Yaklasik dis olculer: 10 x 8 x 5 mm.")),

        # 7. fiyat
        ("fiyat yakala (bos)", yakalar("<sayi> TL", fiyat="")),
        ("fiyat yakala (bicimsiz)", yakalar("<sayi> TL", fiyat="ucretsiz")),
        ("fiyat yakala (eksik TL)", yakalar("<sayi> TL", fiyat="850")),
        ("fiyat gec", temiz(fiyat="1.250 TL")),
        ("parametrik fiyat yakala",
         yakalar("parametrik urunde fiyat", parametrik=True, fiyat="500 TL")),
        ("parametrik fiyat gec", temiz(parametrik=True, fiyat="")),

        # 8. olcu (mm) — CAPALI ifade (denetim-kapisi ile ayni). KUSUR-1: kismi spec-mm capa
        #    ifadesi tasimadigi icin olcusuz sayilir. KUSUR-2: etiketli/parantezli capali biciM
        #    (":taban ... mm", "(15 cm boyda): ...") olculu sayilir (Ictihat 71 korumasi).
        ("olcu yakala", yakalar(
            "olcu (mm)", aciklama="Guzel bir parca, olcusuz aciklama.")),
        ("olcu yakala (kismi spec-mm)", yakalar(
            "olcu (mm)", aciklama="M32×3.5 vida disi, yaklasik 31 mm dis cap. Dayanikli.")),
        ("olcu gec (gomulu capali)", temiz(
            aciklama="Saglam parca. Yaklasik dis olculer: 12 × 8 × 5 mm. Kolay montaj.")),
        ("olcu gec (etiketli capali)", temiz(
            aciklama="Braket. Yaklaşık dış ölçüler: taban 137 × 135 × 70 mm.")),
        ("olcu gec (parantezli capali)", temiz(
            aciklama="Sinyal adaptoru. Yaklaşık dış ölçüler (15 cm boyda): 113 × 117 × 150 mm.")),

        # 9. lisans
        ("lisans yakala (dict degil)",
         yakalar("lisans dict degil", lisans="CC BY 4.0")),
        ("lisans yakala (tur bos)",
         yakalar("lisans.tur bos", lisans={"tasarimci": "x", "tur": ""})),
        ("lisans yakala (tur yok)",
         yakalar("lisans.tur bos", lisans={"tasarimci": "x"})),
        ("lisans gec", temiz(lisans={"tasarimci": "x", "tur": "CC BY 4.0"})),
        ("lisans yok gec", temiz()),  # lisans alani hic yok -> sorun degil
    ]

    # 8b. satin-alma istisnasi: olcu yoksa bile kaynak tur=satin-alma ise gecer
    olcusuz = {"aciklama": "Hazir alinmis parca, olcu satiri yok."}
    kayit_satin = {"olcusuz-urun": {"tur": "satin-alma", "link": "http://x"}}
    kontroller.append((
        "satin-alma istisnasi gec",
        not any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_satin, gid="olcusuz-urun")),
    ))
    # ayni urun satin-alma DEGILSE olcu yoklugu yakalanmali (istisna dar)
    kayit_cc = {"olcusuz-urun": {"tur": "ucretsiz-cc", "link": "http://x"}}
    kontroller.append((
        "satin-alma disi olcu yakala",
        any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_cc, gid="olcusuz-urun")),
    ))
    # kayit str/list bicimindeyse istisna UYGULANMAZ -> olcu yoklugu yakalanir
    kayit_str = {"olcusuz-urun": "https://ornek.test/model"}
    kontroller.append((
        "str kayit istisnasiz",
        any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_str, gid="olcusuz-urun")),
    ))

    # kaynak dosyasi yok/bozuk -> sessizce bos harita, cokme yok
    with_bad = _kaynaklari_oku(os.path.join(ROOT, "yok-boyle-dosya-parti.json"))
    kontroller.append(("kaynak dosyasi yok -> bos", with_bad == {}))

    # parti belirleme: HEAD'de olmayan id'ler yeni sayilir
    urunler = [
        {"id": "eski-urun", "baslik": "Eski"},
        _gecerli_urun(),
    ]
    head = {"eski-urun"}
    bulgular, boyut = _parti_denetle(urunler, head, kaynaklar)
    kontroller.append(("parti sadece yeni urun", boyut == 1 and bulgular == []))

    # yeni urun yoksa parti bos
    _, boyut_bos = _parti_denetle([{"id": "eski-urun"}], {"eski-urun"}, kaynaklar)
    kontroller.append(("parti bos", boyut_bos == 0))

    # HEAD okunamazsa (None) parti belirlenemez
    bnone, cnone = _parti_denetle(urunler, None, kaynaklar)
    kontroller.append(("head yok -> belirlenemez", bnone is None and cnone is None))

    # partide bulgu varsa (gid, aciklama) olarak raporlanir
    kotu = dict(_gecerli_urun())
    kotu["id"] = "yeni-kotu"
    kotu["kategori"] = "Uzay"
    b2, _ = _parti_denetle([{"id": "eski-urun"}, kotu], {"eski-urun"}, kaynaklar)
    kontroller.append((
        "partide bulgu raporlanir",
        any(gid == "yeni-kotu" and "kategori" in msg for gid, msg in (b2 or [])),
    ))

    # -----------------------------------------------------------------
    # MEVCUT-URUN-DEGISIKLIGI (backfill) kipi: RED + KABUL taraflari
    # -----------------------------------------------------------------
    def m_urun(uid, **kw):
        u = dict(_gecerli_urun())
        u["id"] = uid
        u.update(kw)
        return u

    A1 = m_urun("mevcut-a", gorseller=["https://media.pruvo3d.com/urunler/a-1.jpg"])
    B1 = m_urun("mevcut-b", gorseller=["https://media.pruvo3d.com/urunler/b-1.jpg"])
    onceki = [A1, B1]

    # KABUL: mesru backfill — A'ya gecerli 2. gorsel eklendi; sayi + id sabit
    A2 = m_urun("mevcut-a", gorseller=[
        "https://media.pruvo3d.com/urunler/a-1.jpg",
        "https://media.pruvo3d.com/urunler/a-2.jpg"])
    kontroller.append(("backfill mesru KABUL",
                       _mevcut_denetle(onceki, [A2, B1], strict=True) == []))

    # RED: urun sayisi degisti (yeni urun eklendi) — strict
    yeni_c = m_urun("mevcut-c")
    kontroller.append(("backfill sayi degisti RED", any(
        "sayisi degisti" in m for _, m in _mevcut_denetle(onceki, [A1, B1, yeni_c], strict=True))))

    # RED: gecersiz URL semasi (http / yanlis host)
    A_bad = m_urun("mevcut-a", gorseller=[
        "https://media.pruvo3d.com/urunler/a-1.jpg", "http://kotu/x.jpg"])
    kontroller.append(("backfill gecersiz URL RED", any(
        "gecersiz gorsel URL" in m for _, m in _mevcut_denetle(onceki, [A_bad, B1], strict=True))))

    # RED: mevcut id kayboldu (B -> C, sayi ayni kalir; id kumesi bozulur)
    kontroller.append(("backfill id kayboldu RED", any(
        "kayboldu" in m for _, m in _mevcut_denetle(onceki, [A1, yeni_c], strict=True))))

    # RED: strict backfill'de yeni id belirmesi (ayni swap; sayi sabit ama id eklendi)
    kontroller.append(("backfill yeni id belirdi RED", any(
        "yeni id belirdi" in m for _, m in _mevcut_denetle(onceki, [A1, yeni_c], strict=True))))

    # RED: backfill-disi alan (fiyat) sessizce degisti
    A_fiyat = m_urun("mevcut-a", fiyat="9999 TL")
    kontroller.append(("backfill disi alan RED", any(
        "'fiyat'" in m for _, m in _mevcut_denetle(onceki, [A_fiyat, B1], strict=True))))

    # default (non-strict): mesru yeni urun eklemek mevcut-kipini KIRMIZI YAPMAZ
    kontroller.append(("mevcut kip yeni urune dokunmaz",
                       _mevcut_denetle(onceki, [A1, B1, yeni_c], strict=False) == []))

    # default (non-strict): mevcut urun SILME yine de RED (silme daima kotu)
    kontroller.append(("mevcut kip silmeyi yakalar", any(
        "kayboldu" in m for _, m in _mevcut_denetle(onceki, [A1], strict=False))))

    # KIRMIZI-MUTASYON kanit destekleyicisi: gorseller degismemisse hicbir sey demez
    kontroller.append(("degismeyen urun temiz",
                       _mevcut_denetle(onceki, [A1, B1], strict=True) == []))

    # -----------------------------------------------------------------
    # BACKFILL kolunda GORSELSIZ DAR ISTISNA (yeni-urun koluyla AYNI karar)
    # -----------------------------------------------------------------
    # F1: HEAD'de zaten bayrakli FIZIKSEL urun; gorseller bosaldi -> KABUL
    F1 = m_urun("mevcut-f", tur="fiziksel", gorselsiz=True,
                gorseller=["https://media.pruvo3d.com/urunler/f-1.jpg"])
    F2 = m_urun("mevcut-f", tur="fiziksel", gorselsiz=True, gorseller=[])
    kontroller.append(("backfill bayrakli fiziksel bosalma KABUL",
                       _mevcut_denetle([F1], [F2], strict=True) == []))

    # F3: ayni sey BAYRAKSIZ -> KIRMIZI (varsayilan zorunluluk backfill'de de duruyor)
    G1 = m_urun("mevcut-g", tur="fiziksel",
                gorseller=["https://media.pruvo3d.com/urunler/g-1.jpg"])
    G2 = m_urun("mevcut-g", tur="fiziksel", gorseller=[])
    kontroller.append(("backfill bayraksiz bosalma KIRMIZI", any(
        "gorseller bos" in m for _, m in _mevcut_denetle([G1], [G2], strict=True))))

    # F4: BASKI urunu bayrakli olsa da bosalamaz -> KIRMIZI
    H1 = m_urun("mevcut-h", gorselsiz=True,
                gorseller=["https://media.pruvo3d.com/urunler/h-1.jpg"])
    H2 = m_urun("mevcut-h", gorselsiz=True, gorseller=[])
    kontroller.append(("backfill bayrakli baski bosalma KIRMIZI", any(
        "gorseller bos" in m for _, m in _mevcut_denetle([H1], [H2], strict=True))))

    # F5: istisna URL semasini ACMAZ (bayrakli fiziksel urunde bile)
    F_bad = m_urun("mevcut-f", tur="fiziksel", gorselsiz=True,
                   gorseller=["http://kotu/x.jpg"])
    kontroller.append(("backfill bayrakli gecersiz URL KIRMIZI", any(
        "gecersiz gorsel URL" in m for _, m in _mevcut_denetle([F1], [F_bad], strict=True))))

    # F6: bayragin KENDISI backfill'de eklenemez (backfill-disi alan kurali durur)
    kontroller.append(("backfill bayrak eklemek KIRMIZI", any(
        "'gorselsiz'" in m for _, m in _mevcut_denetle([G1], [
            m_urun("mevcut-g", tur="fiziksel", gorselsiz=True, gorseller=[])],
            strict=True))))

    # -----------------------------------------------------------------
    # GORUNURLUK: muafiyet sayaci (sessiz muafiyet = yeni korluk)
    # -----------------------------------------------------------------
    muaf_urun = m_urun("muaf-anod", tur="fiziksel", gorselsiz=True, gorseller=[])
    normal_urun = m_urun("normal-urun")
    kontroller.append((
        "parti muaf sayimi",
        _parti_muaflar([normal_urun, muaf_urun, {"id": "eski-urun"}], {"eski-urun"})
        == ["muaf-anod"],
    ))
    kontroller.append((
        "parti muaf sayimi (muaf yoksa bos)",
        _parti_muaflar([normal_urun], set()) == [],
    ))
    kontroller.append((
        "backfill muaf sayimi",
        _mevcut_muaflar([F1], [F2]) == ["mevcut-f"],
    ))
    kontroller.append((
        "backfill muaf sayimi (bayraksiz sayilmaz)",
        _mevcut_muaflar([G1], [G2]) == [],
    ))
    kontroller.append(("muaf satiri sayi + id basar",
                       _muaf_satiri(["a", "b"]) == "gorselsiz kabul edilen: 2 (a, b)"))
    kontroller.append(("muaf satiri sifir basar",
                       _muaf_satiri([]) == "gorselsiz kabul edilen: 0"))

    # sayac TEMIZ kosumda da, BULGULU kosumda da basilmali (susturma mutasyonu olur)
    temiz_satirlar, temiz_rc = _rapor_satirlari([], 2, [], [], set(), ["muaf-anod"])
    kontroller.append((
        "rapor temiz kosumda sayac basar",
        temiz_rc == 0 and any("gorselsiz kabul edilen: 1 (muaf-anod)" in s
                              for s in temiz_satirlar)
        and any("parti temiz" in s for s in temiz_satirlar),
    ))
    kirli_satirlar, kirli_rc = _rapor_satirlari(
        [("kotu", "kategori gecersiz")], 2, [], [], set(), ["muaf-anod"])
    kontroller.append((
        "rapor bulgulu kosumda da sayac basar",
        kirli_rc == 1 and any("gorselsiz kabul edilen: 1 (muaf-anod)" in s
                              for s in kirli_satirlar)
        and any(s.startswith("SORUN kotu:") for s in kirli_satirlar),
    ))
    yok_satirlar, yok_rc = _rapor_satirlari([], 0, [], [], set(), [])
    kontroller.append((
        "rapor parti yok davranisi korundu",
        yok_rc == 0 and yok_satirlar == ["parti yok: working tree = HEAD"],
    ))

    hatalar = [ad for ad, gecti in kontroller if not gecti]
    if hatalar:
        for ad in hatalar:
            print("TEST KALDI: %s" % ad, file=sys.stderr)
        return 1
    print("TEST GECTI")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true",
                    help="bellek ici oz-sinamayi calistir (gercek dosyaya dokunmaz)")
    ap.add_argument("--backfill", action="store_true",
                    help="strict backfill kipi: urun sayisi + id kumesi SABIT olmali "
                         "(yeni/silinen urun -> RED). Sadece mevcut alan guncellemesi beklenir.")
    args = ap.parse_args()

    if args.test:
        return _oz_sinama()

    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
    except (OSError, ValueError) as e:
        print("HATA: urunler.json okunamadi: %s" % e, file=sys.stderr)
        return 2
    if not isinstance(urunler, list):
        print("HATA: urunler.json bir dizi degil.", file=sys.stderr)
        return 2

    head_urunler = _head_urunler()
    if head_urunler is None:
        print("parti belirlenemedi: HEAD:urunler.json okunamadi")
        return 0
    head_ids = _ids_kumesi(head_urunler)

    kaynaklar = _kaynaklari_oku(KAYNAKLAR)

    # 1. YENI-URUN kipi (HEAD'de olmayan id'ler)
    yeni_bulgular, yeni_boyut = _parti_denetle(urunler, head_ids, kaynaklar)
    # 2. MEVCUT-URUN-DEGISIKLIGI kipi (backfill: HEAD'de var olan urunler)
    mevcut_bulgular = _mevcut_denetle(head_urunler, urunler, kaynaklar, strict=args.backfill)
    degisen, silinen = _mevcut_degisenler(head_urunler, urunler)
    # gorunurluk: gorsel muafiyeti uygulanan satirlar (yeni + backfill)
    muaf_idler = (_parti_muaflar(urunler, head_ids)
                  + _mevcut_muaflar(head_urunler, urunler))

    satirlar, rc = _rapor_satirlari(yeni_bulgular, yeni_boyut, mevcut_bulgular,
                                    degisen, silinen, muaf_idler)
    for satir in satirlar:
        print(satir)
    return rc


if __name__ == "__main__":
    sys.exit(main())
