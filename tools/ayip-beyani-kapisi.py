#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AYIP BEYANI KAPISI — 6502 m.11'in DORT secimlik hakki, SARTSIZ, her sayfa govdesinde.

NEDEN VAR (K64, 12 Agu 2026 — olculdu):
    grep -rilE '6502|bedel indirimi|bedel iadesi' tools   -> 6 dosya
    ... ayni desen `--include='*kapi*.py'`                 -> 0 KAPI
Yani hukuki metin repoda VARDI ama onu OLCEN nobetci YOKTU. Uc hukuk kapisi
(cayma-beyani · landing-hukuk · bayat-beyan) duzeltme ONCESI dar metinde de YESILDI:
"ayipli bir urun ucretsiz onarilir ya da degistirilir" kalibi yalniz IKI secenegi anar,
hakki "kusur bizdense" diye SARTA baglar ve bedel indirimi / bedel iadesi secenegini hic
anmaz. PR #66/#67 bunu 35 govdede genisletti; regresyon (yeni sayfa dar kalipla gelir)
hicbir yerde kirmizi yakmazdi. Bu kapi o ekseni kapatir.

KURAL (tek eksen, tek hukum):
    Cayma hakkinin kullanilamadigini soyleyen ya da AYIP'tan soz eden HER sayfa govdesi,
    kanonik ayip beyanini BIREBIR tasimak zorundadir.
Kanonik metin BU DOSYADA YAZILI DEGILDIR: tools/sayfalar.py::AYIP_HAKLARI_CUMLESI'nden
okunur ve o cumle de AYIP_HAKLARI_SECENEKLERI demetinden TURETILIR (ikiz tanim yok;
hukuki metin degisirse kapi pesinden gelir, ayrisma fail-closed kirmizi yakar).

    ⚠️ "BIREBIR" olcusu ASIRI DEGILDIR, OLCULDU: bugunku katalogda kanonik cumleyi
    tasiyan govde sayisi (57) ile DORT SECENEGI birlikte tasiyan govde sayisi (57)
    ESITTIR. Yani birebir kural, "dort secenek" kuralindan TEK BIR sayfa bile fazla
    kirmizi yakmaz; kazanci sartsizligi da tek olcumde garanti etmesidir (secenekleri
    bir kosul cumlesine gomen metin birebir esitligi bozar).

KAPSAM (orneklem YOK):
    * sayfalar.CONTENT_PAGES — 366 uretilen govde; BAGLAYICI yasal sayfalar
      (/teslimat-iade, /mesafeli-satis) BU LISTENIN ICINDEDIR, muaf DEGILDIR.
    * sayfalar.STATIK_SAYFALAR — elle yazilmis, repoda commit'li <slug>/index.html.
    🔴 KAPSAM DISI + GEREKCELI (sessiz degil): secenekler.js::BEYAN CAYMA_* satirlari.
      O yuzeyin sahibi tools/cayma-beyani-kapisi.py'dir (B2/B5/B8/B10) ve orada OLCULMUS
      bir mimar karari vardir: urun/sepet panelinde hak REDDI de hak BEYANI de yazilmaz,
      hakkin kapsami BAGLAYICI YASAL GOVDEDE anlatilir. Bu kapinin ayni yuzeye ikinci
      bir hukum yazmasi o karari sessizce gevsetirdi.

FAIL-CLOSED: kanonik sabit okunamaz/bozuksa, kapsam bossa, bir govde render edilemezse
-> OLCULEMEDI + sifir-disi cikis. "Sapma yok" hukmu ANCAK pozitif taramadan turer.

Kullanim:
    python3 tools/ayip-beyani-kapisi.py                # gercek tarama (hukum)
    python3 tools/ayip-beyani-kapisi.py --kendini-test # sentetik fiksturlerle oz-test
Cikis: 0 = sapan yok · 1 = sapan var / oz-test kirmizi · 2 = OLCULEMEDI.
"""
import os
import re
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)

# --- IDDIA AILELERI (mutasyon kabulu `rc` ile DEGIL bu IZ ile yapilir) ---------------
#   KANON-SEMA  : kanonik kaynagin kendisi (demet + turetilen cumle) tutarli mi
#   KAPSAM      : hangi govde taramaya GIRIYOR (tetik) + kapsam bos/okunamaz mi
#   SAPMA       : kapsamdaki govde kanonik beyani tasiyor mu
#   CELISKI     : kanonik cumlenin yaninda dar/sartli eski kalip da yasiyor mu
#   TEMIZ-SAYIM : insana basilan ozet, hukmu besleyen KUMEDEN mi turuyor
AILELER = ("KANON-SEMA", "KAPSAM", "SAPMA", "CELISKI", "TEMIZ-SAYIM")


class Olculemedi(RuntimeError):
    pass


# --- TETIK: hangi govde bu kuralin kapsamindadir ------------------------------------
# (a) cayma hakkinin KULLANILAMADIGINI soyleyen govde — tuketiciye "hakkin yok" denen yer,
# (b) AYIP'tan soz eden govde — "bu ayip degildir" diyen sayfa da dahildir; hakkin
#     SINIRINI anlatan sayfa, hakkin KENDISINI de tam soylemek zorundadir.
# 🔴 KELIME SINIRI SART: cikarilmis "ayıp" alt-dizesi "kayıp" kelimesinin ICINDE de gecer;
#    sinirsiz desen 366 govdenin buyuk kismini yanlislikla kapsama alirdi (olculdu).
_ONEK = "a-zçğıöşü"
TETIK_CAYMA = re.compile(
    r"cayma hakk[ıi][^.;]{0,90}?"
    r"(bulunmaz|yoktur|kullanılamaz|kullanılmaz|işlemez|kapsamı dışında)")
TETIK_AYIP = re.compile(r"(?<![" + _ONEK + r"])ayıp")

# Kanonik dort secenegin yaninda yasadiginda hakki iki secenege daraltan veya hakka
# kosul ekleyen eski kaliplar. Tek sabit: hukum ve sentetik fiksturler ayni ekseni olcer.
CELISKILI_DAR_KALIPLAR = re.compile(
    r"(?:ücretsiz\s+onar(?:ılır|ır)\s+(?:ya\s+da|veya)\s+"
    r"(?:yenisiyle\s+)?değiştir(?:ilir|iriz)|"
    r"onarım\s+(?:ya\s+da|veya)\s+değişim|"
    r"kusur\s+bizdense|"
    r"sapma\s+bizim(?:\s+aldığımız)?\s+ölçümüzden\s+kaynaklanıyorsa)"
)


def kucult(s):
    """Turkce-duyarli kucultme (I -> ı, İ -> i)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def etiketsiz(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def kanon():
    """Kanonik ayip beyani — TEK KAYNAK sayfalar.py. Doner: (cumle, secenekler, kanun_no).

    Fail-closed: sabitlerden biri yoksa/bozuksa Olculemedi. Kapi kendi kopyasini TUTMAZ."""
    sys.path.insert(0, BURASI)
    try:
        import sayfalar
    except Exception as hata:
        raise Olculemedi("sayfalar.py import edilemedi -> %r" % (hata,))
    try:
        cumle = sayfalar.AYIP_HAKLARI_CUMLESI
        secenekler = tuple(sayfalar.AYIP_HAKLARI_SECENEKLERI)
        kanun_no = sayfalar.AYIP_KANUN_NO
    except AttributeError as hata:
        raise Olculemedi("kanonik ayip sabiti sayfalar.py'de YOK -> %r" % (hata,))
    return cumle, secenekler, kanun_no


def kanon_semasi(cumle, secenekler, kanun_no):
    """KANON-SEMA ailesi: kanonik kaynagin kendisi ayakta mi? Hata listesi doner.

    6502 m.11 DORT secimlik hak tanir; demet dortten sapiyorsa ya da turetilen cumle
    demeti/kanun atfini tasimiyorsa kapi HICBIR govdeyi olcmeden KIRMIZI yanar."""
    hatalar = []
    if len(secenekler) != 4:
        hatalar.append("6502 m.11 DORT secenek tanir, demette %d var" % len(secenekler))
    if len(set(kucult(s).strip() for s in secenekler)) != len(secenekler):
        hatalar.append("secenek demetinde MUKERRER giris var")
    for s in secenekler:
        if not isinstance(s, str) or not s.strip():
            hatalar.append("bos/gecersiz secenek girisi: %r" % (s,))
    c = kucult(cumle or "")
    if not c.strip():
        hatalar.append("kanonik cumle BOS")
    for s in secenekler:
        if kucult(s) not in c:
            hatalar.append("turetilen cumle '%s' secenegini TASIMIYOR" % s)
    if not (kanun_no or "").strip() or kanun_no not in (cumle or ""):
        hatalar.append("kanonik cumle kanun atfini (%r) TASIMIYOR" % (kanun_no,))
    return hatalar


def kapsamda(govde_kucuk):
    return bool(TETIK_CAYMA.search(govde_kucuk)) or bool(TETIK_AYIP.search(govde_kucuk))


def _sapma_sebebi(g, cumle, secenekler, kanun_no):
    """Kanonik beyani TASIMAYAN govde icin insan-okur sebep. Hukmu DEGISTIRMEZ."""
    eksik = [s for s in secenekler if kucult(s) not in g]
    if eksik:
        return "eksik secenek: " + ", ".join(eksik)
    if kanun_no not in g:
        return "dort secenek var ama %s atfi YOK" % kanun_no
    return "dort secenek + atif var ama KANONIK cumle degil (sarta baglanmis/parcalanmis)"


def hukum(yuzeyler, cumle, secenekler, kanun_no):
    """TEK HUKUM NOKTASI. yuzeyler = ((ad, govde_html), ...) -> (kapsam, sapan).

    kapsam: kurala tabi (ad, govde_kucuk) listesi · sapan: (ad, sebep) listesi.
    Insana basilan HER sayi bu iki listeden turer — ikinci sayim noktasi ACILMAZ."""
    kapsam, sapan = [], []
    kanonik = kucult(cumle)
    for ad, html in yuzeyler:
        g = kucult(etiketsiz(html))
        if not g.strip():
            raise Olculemedi("bos govde -> %s" % ad)
        if not kapsamda(g):
            continue
        kapsam.append((ad, g))
        if kanonik not in g:
            sapan.append((ad, _sapma_sebebi(g, cumle, secenekler, kanun_no)))
        elif CELISKILI_DAR_KALIPLAR.search(g):
            sapan.append((ad, "kanonik cumle VAR ama celiskili dar kalip DA var"))
    return kapsam, sapan


def yuzeyleri_topla():
    """Taranan TUM hukuk yuzeyleri. Orneklem YOK; okuma hatasi -> Olculemedi."""
    sys.path.insert(0, BURASI)
    try:
        import sayfalar
    except Exception as hata:
        raise Olculemedi("sayfalar.py import edilemedi -> %r" % (hata,))

    yuzeyler = []
    if not sayfalar.CONTENT_PAGES:
        raise Olculemedi("CONTENT_PAGES BOS")
    for kayit in sayfalar.CONTENT_PAGES:
        try:
            slug, _baslik, _meta, uretici = kayit
            yuzeyler.append((slug, uretici()))
        except Exception as hata:
            raise Olculemedi("sayfa render edilemedi (%r) -> %r" % (kayit, hata))
    if not sayfalar.STATIK_SAYFALAR:
        raise Olculemedi("STATIK_SAYFALAR BOS")
    for slug in sayfalar.STATIK_SAYFALAR:
        yol = os.path.join(KOK, slug, "index.html")
        if not os.path.isfile(yol):
            raise Olculemedi("statik sayfa diskte YOK -> %s" % yol)
        with open(yol, encoding="utf-8") as f:
            yuzeyler.append(("statik:" + slug, f.read()))
    return yuzeyler


def _bas_iz(aile, mesaj):
    print("🔴 IZ=%s %s" % (aile, mesaj))


# ------------------------------------------------------------------ OZ-TEST
_F_TEMIZ = ("<p>Ölçüye özel hazırlanan üründe cayma hakkı bulunmaz; %s</p>")
_F_DAR = ("<p>Ölçüye özel üretilen üründe cayma hakkı bulunmaz, ama ayıplı bir ürün "
          "ücretsiz onarılır ya da değiştirilir.</p>")
_F_UC = ("<p>Cayma hakkı kullanılamaz; ayıplı üründe 6502 sayılı Kanun'dan doğan "
         "haklarınız aynen durur — ücretsiz onarım, yenisiyle değişim ya da bedel "
         "iadesi seçenekleri saklıdır.</p>")
_F_SARTLI = ("<p>Cayma hakkı bulunmaz; sapma bizim ölçümüzden kaynaklanıyorsa 6502 "
             "sayılı Kanun uyarınca ücretsiz onarım, yenisiyle değişim, bedel indirimi "
             "ya da bedel iadesi uygularız.</p>")
_F_ILGISIZ = "<p>Kayıp bir tırnak yerine yenisini üretiriz; kayıp parça sorun değildir.</p>"
_F_CELISKI_DAR = ("<p>%s Buna karşılık ayıplı bir ürün ücretsiz onarılır ya da "
                   "değiştirilir.</p>")
_F_CELISKI_SARTLI = ("<p>%s Ancak kusur bizdense bu haklar uygulanır.</p>")


def kendini_test():
    """Kapinin KENDI iddialari. Her kirmizi iddia AILE IZI ile basilir."""
    iddia, kirmizi = 0, 0

    try:
        cumle, secenekler, kanun_no = kanon()
    except Olculemedi as hata:
        _bas_iz("KANON-SEMA", "kanonik kaynak okunamadi: %s" % hata)
        print("OZ-TEST KIRMIZI: 1/1 iddia")
        return 1

    # --- KANON-SEMA
    iddia += 1
    hatalar = kanon_semasi(cumle, secenekler, kanun_no)
    if hatalar:
        kirmizi += 1
        _bas_iz("KANON-SEMA", "kanonik kaynak tutarsiz: " + " | ".join(hatalar))

    iddia += 1
    if kanon_semasi(cumle, secenekler[:2], kanun_no) == []:
        kirmizi += 1
        _bas_iz("KANON-SEMA", "iki secenekli demet KABUL EDILDI (dort sarti olu)")

    # 🔴 AYRISMA: cumle demetten TURETILIR, dolayisiyla gercek sabitte iki taraf DAIMA
    # tutarlidir ve "cumle secenekleri tasiyor mu" kolu tautoloji gibi gorunur. Ayrisma
    # SENTETIK olarak uretilir: biri surulunce sema KIRMIZI yanmali (olculdu: bu iddia
    # yokken 'kol tamamen olu' mutanti HAYATTA KALIYORDU).
    iddia += 1
    if kanon_semasi(cumle.replace(secenekler[2], "xxx"), secenekler, kanun_no) == []:
        kirmizi += 1
        _bas_iz("KANON-SEMA", "cumle bir secenegi KAYBETTIGI halde sema yesil kaldi")

    iddia += 1
    if kanon_semasi(cumle.replace(kanun_no, "0000"), secenekler, kanun_no) == []:
        kirmizi += 1
        _bas_iz("KANON-SEMA", "cumle kanun atfini KAYBETTIGI halde sema yesil kaldi")

    temiz = _F_TEMIZ % cumle
    # --- KAPSAM
    # 🔴 `_F_SARTLI` govdesinde "ayıp" kelimesi GECMEZ: kapsama YALNIZ cayma-yok tetigiyle
    #    girer. Bu fikstur olmadan tetigin cayma kolu silinse SAPMA ailesinden kirmizi
    #    gelir ve KAPSAM ekseni kanitsiz kalirdi (olculdu, mutant K64-M3).
    for etiket, govde, bekle in (("cayma-yok govde", _F_DAR, True),
                                 ("cayma-yok, 'ayıp' GECMEYEN govde", _F_SARTLI, True),
                                 ("kanonik govde", temiz, True),
                                 ("ilgisiz govde (kayıp!)", _F_ILGISIZ, False)):
        iddia += 1
        var = kapsamda(kucult(etiketsiz(govde)))
        if var != bekle:
            kirmizi += 1
            _bas_iz("KAPSAM", "%s -> kapsam=%s (beklenen %s)" % (etiket, var, bekle))

    iddia += 1
    try:
        hukum((), cumle, secenekler, kanun_no)
        bos_kapsam = True
    except Olculemedi:
        bos_kapsam = True
    if not bos_kapsam:
        kirmizi += 1

    iddia += 1
    try:
        hukum((("bos", "<p>   </p>"),), cumle, secenekler, kanun_no)
        kirmizi += 1
        _bas_iz("KAPSAM", "bos govde OLCULEMEDI vermedi (fail-open)")
    except Olculemedi:
        pass

    # --- SAPMA
    fikstur = (("temiz", temiz), ("yalniz-kanonik", _F_TEMIZ % cumle),
               ("kanonik-arti-dar", _F_CELISKI_DAR % cumle),
               ("kanonik-arti-sartli", _F_CELISKI_SARTLI % cumle),
               ("dar", _F_DAR), ("uc-secenek", _F_UC),
               ("sartli", _F_SARTLI), ("ilgisiz", _F_ILGISIZ))
    kapsam, sapan = hukum(fikstur, cumle, secenekler, kanun_no)
    sapan_adlar = [a for a, _ in sapan]

    iddia += 1
    if "temiz" in sapan_adlar:
        kirmizi += 1
        _bas_iz("SAPMA", "kanonik beyani tasiyan govde SAPAN sayildi (yanlis-pozitif)")

    iddia += 1
    if "yalniz-kanonik" in sapan_adlar:
        kirmizi += 1
        _bas_iz("CELISKI", "yalniz kanonik cumle SAPAN sayildi (yanlis-pozitif)")

    for ad in ("kanonik-arti-dar", "kanonik-arti-sartli"):
        iddia += 1
        if ad not in sapan_adlar:
            kirmizi += 1
            _bas_iz("CELISKI", "%s govdesindeki celiski SAPAN sayilmadi" % ad)

    for ad in ("dar", "uc-secenek", "sartli"):
        iddia += 1
        if ad not in sapan_adlar:
            kirmizi += 1
            _bas_iz("SAPMA", "%s govdesi SAPAN sayilmadi (dar beyan geciyor)" % ad)

    iddia += 1
    sebepler = dict(sapan)
    if "bedel indirimi" not in sebepler.get("uc-secenek", ""):
        kirmizi += 1
        _bas_iz("SAPMA", "eksik secenek sebebi 'bedel indirimi'yi adlandirmiyor: %r"
                % sebepler.get("uc-secenek"))

    iddia += 1
    if "ilgisiz" in [a for a, _ in kapsam]:
        kirmizi += 1
        _bas_iz("KAPSAM", "ilgisiz govde kapsama girdi (kayıp -> ayıp alt-dizesi)")

    # --- TEMIZ-SAYIM: insana basilan ozet hukum kumesinden turemeli
    iddia += 1
    if ozet_sayilari(kapsam, sapan) != (len(kapsam), len(sapan), len(kapsam) - len(sapan)):
        kirmizi += 1
        _bas_iz("TEMIZ-SAYIM", "ozet sayilari hukum kumesinden turemiyor")

    iddia += 1
    _, bos_sapan = hukum((("temiz", temiz),), cumle, secenekler, kanun_no)
    if ozet_sayilari([("temiz", "x")], bos_sapan)[1] != 0:
        kirmizi += 1
        _bas_iz("TEMIZ-SAYIM", "sapan yokken ozet sifir-disi sapan bildirdi")

    if kirmizi:
        print("OZ-TEST KIRMIZI: %d/%d iddia" % (kirmizi, iddia))
        return 1
    print("oz-test YESIL: %d iddia" % iddia)
    return 0


def ozet_sayilari(kapsam, sapan):
    """Insana basilan UC sayi — HUKMU BESLEYEN kumelerden turer, yeniden sayilmaz."""
    return (len(kapsam), len(sapan), len(kapsam) - len(sapan))


def main(argv):
    if "--kendini-test" in argv:
        return kendini_test()
    try:
        cumle, secenekler, kanun_no = kanon()
        hatalar = kanon_semasi(cumle, secenekler, kanun_no)
        if hatalar:
            for h in hatalar:
                _bas_iz("KANON-SEMA", h)
            print("OLCULEMEDI: kanonik kaynak tutarsiz")
            return 2
        yuzeyler = yuzeyleri_topla()
        kapsam, sapan = hukum(yuzeyler, cumle, secenekler, kanun_no)
    except Olculemedi as hata:
        _bas_iz("KAPSAM", str(hata))
        print("OLCULEMEDI: %s" % hata)
        return 2

    if not kapsam:
        _bas_iz("KAPSAM", "hicbir govde kapsama girmedi — tetik olmus olabilir")
        print("OLCULEMEDI: kapsam BOS")
        return 2

    kapsam_n, sapan_n, temiz_n = ozet_sayilari(kapsam, sapan)
    print("taranan yuzey: %d" % len(yuzeyler))
    print("kapsam (cayma-yok / ayip beyani gecen): %d" % kapsam_n)
    print("kanonik beyani tasiyan: %d" % temiz_n)
    for ad, sebep in sapan:
        print("  🔴 SAPAN %-58s %s" % (ad, sebep))
    print("SAPAN=%d" % sapan_n)
    if sapan_n:
        print("KIRMIZI — dar/sartli ayip beyani: %d yuzey" % sapan_n)
        return 1
    print("YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
