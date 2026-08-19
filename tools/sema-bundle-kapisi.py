#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEMA BUNDLE KAPISI — shop/src/semalar.js'i jenerator/urunler/'den TURETIR + DRIFT'i bloklar.

NEDEN VAR (sessiz-hata sinifi, PARA):
  Sari seri ("olcuye ozel", parametrik) urunlerin fiyati SUNUCUDA semadan hesaplanir
  (shop/src/parametrik.js). Worker'da dosya sistemi/glob YOK; wrangler(esbuild) yalniz
  STATIK import'lari bundle'a katar -> semalar.js uzun sure 23 satirlik ELLE YAZILMIS bir
  import listesiydi. Liste ile jenerator/urunler/ dizini ayrisirsa hata SESSIZDIR:
    * dizinde VAR, listede YOK  -> SEMALAR.get(id) undefined -> shop/src/index.js kalemi
      "parametrik-urun" 400'u ile WhatsApp'a dusurur. Urun sitede satiliyor gorunur, kartla
      TAHSIL EDILEMEZ. Kimse bakmadikca gorunmez = sessiz gelir kaybi.
    * listede VAR, dizinde YOK  -> esbuild import'u cozemez, bundle KURULMAZ (deploy aninda
      patlar; en azindan gurultulu).
    * iki sema AYNI id'yi tasir -> `new Map(HEPSI.map(s => [s.id, s]))` SESSIZCE SON kaydi
      tutar; bir urun BASKA bir semanin matematigiyle fiyatlanir = YANLIS TUTAR TAHSILI.
    * semanin `id`'si yok/bos   -> kayit sessizce erisilemez olur (yukaridaki 1. hal).
  Bugun bu kanal ACIK (secenekler.js PARAMETRIK_ODEME_ACIK = true, 23/23 semada
  tabanFiyatTL dolu) -> liste kayarsa dogrudan para etkilenir.

  Eskiden tek koruma shop/test/kabul.js test 9(a) idi; o suite `wrangler dev --local` + ag
  istedigi icin ci-kapsam-test.py'de MUAFTI -> koruma FIILEN HIC KOSMUYORDU.

COZUM (konfigur-bundle-kapisi.py ile AYNI DESEN — ikinci desen icat edilmedi):
  Artefakt ELLE YAZILMAZ, TEK KAYNAKTAN (jenerator/urunler/*.json dizini) TURETILIR.
  Bu dosya hem URETICI (--yaz) hem KAPI'dir (varsayilan: karsilastir, sapma -> exit 1).

  TURETME mi DOGRULAMA mi? -> TURETME. Gerekce: (1) konfigur ekseninde secilen desen bu;
  (2) "liste == dizin" BIREBIR invaryanti zaten vardi (kabul testi 9a) -> turetme yeni bir
  semantik EKLEMEZ, yalnizca elle bakimi ortadan kaldirir; (3) dogrulama-only birakmak
  artefakti ELLE YAZILAN dosya olarak birakirdi — oldurulmek istenen sey tam olarak buydu.

KAPSAM — DAR EKSEN ([[kapi-kapsam-eksen-secimi]]):
  Kapi YALNIZ iki seye bakar: jenerator/urunler/ altindaki .json dosyalari ve
  shop/src/semalar.js. urunler.json'a urun eklemek/silmek, fiyat/gorsel/aciklama duzenlemek,
  index.html/CSS/tools degistirmek, dizine .json OLMAYAN dosya koymak, sema dosyasinin
  ICERIGINI (parametre/fiyat) degistirmek turetilen ciktiyi DEGISTIRMEZ -> kapi YESIL kalir.
  Yani rutin urun partisi ve normal kod commit'i TUM EKIBIN yayinini durdurmaz
  (olcum: --kendini-test bolum A).

FAIL-CLOSED:
  * Kaynak dizin okunamaz/yok    -> OLCULEMEDI + exit 3 ("yesil" DEGIL).
  * Sema JSON'u ayristirilamaz   -> OLCULEMEDI + exit 3.
  * Sema `id`'si yok/bos/metin degil, ya da IKI sema AYNI id -> KIRMIZI + exit 1, artefakt
    URETILMEZ (yarim/yanlis-anahtarli bundle ship edilmez).
  * Artefakt bayat/elle degistirilmis -> KIRMIZI + exit 1. Sessiz gecis yolu YOKTUR.

KULLANIM:
    python3 tools/sema-bundle-kapisi.py                # KAPI (CI): sapma -> exit 1
    python3 tools/sema-bundle-kapisi.py --yaz          # artefakti URET (tek bakim komutu)
    python3 tools/sema-bundle-kapisi.py --kendini-test # yanlis-pozitif + kirmizi-mutasyon
    python3 tools/sema-bundle-kapisi.py --kaynak X --dosya Y   # fikstur yollari
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAYNAK_VARSAYILAN = os.path.join(ROOT, "jenerator", "urunler")
ARTEFAKT_VARSAYILAN = os.path.join(ROOT, "shop", "src", "semalar.js")

# Artefakttan kaynak dizine GORECE import oneki. shop/src/x.js -> ../../jenerator/urunler/
IMPORT_ONEK = "../../jenerator/urunler/"

# Cikis kodu sozlesmesi (yonetici ilke: hicbir ariza yolu 0 uretemez).
RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 3

BASLIK = """/**
 * URETILMIS DOSYA — ELLE DUZENLEME (elle yapilan degisiklik ilk uretimde KAYBOLUR).
 *
 * KAYNAK: jenerator/urunler/*.json — parametrik ("olcuye ozel", sari seri) urun semalari.
 * URET  : python3 tools/sema-bundle-kapisi.py --yaz
 * KAPI  : python3 tools/sema-bundle-kapisi.py   (deploy.yml'de BLOKLAYICI; liste bayatsa
 *         CI KIRMIZI yanar -> "yeni sema eklendi, import listesi guncellenmedi" penceresi
 *         kapali)
 *
 * NEDEN STATIK IMPORT LISTESI: Worker'da dosya sistemi/glob YOK; wrangler(esbuild) yalniz
 * statik import'lari bundle'a katar. Liste dizinden AYRISIRSA hata SESSIZDIR — sema
 * bulunamayan sari urun kartla tahsil edilemez (shop/src/index.js "parametrik-urun" 400 ->
 * WhatsApp), ayni id'yi tasiyan iki sema ise sessizce YANLIS FIYAT uretir. Kapi ikisini de
 * uretimden ONCE bloklar.
 *
 * Semalar public veri (matematik + aralik); sir icermez (gizlilik: tedarikci izi yok).
 */
"""

GOVDE_YORUM = ("// Anahtar semanin KENDI id'sinden gelir (dosya adindan degil): sema id'si "
               "urunler.json'daki\n"
               "// kebab-id ile eslesmezse zaten sema bulunamaz ve odeme reddedilir. Kapi "
               "id'lerin VAR ve\n"
               "// BENZERSIZ oldugunu uretimden once dogrular (ayni id -> Map sessizce SON "
               "kaydi tutardi).")

_GECERSIZ = re.compile(r"[^0-9A-Za-z]")


class Olculemedi(Exception):
    """Kaynak okunamadi — 'yesil' degil, OLCULEMEDI (exit 3)."""


class Kirmizi(Exception):
    """Kaynak okundu ama icerik kabul edilemez (exit 1)."""


def _tanimlayici(ad):
    """Dosya adindan deterministik, gecerli bir JS tanimlayicisi turetir."""
    return "s_" + _GECERSIZ.sub("_", ad)


def semalari_oku(kaynak_dizin):
    """Kaynak dizinden [(dosya_adi_uzantisiz, sema_objesi)] (ada gore SIRALI) dondurur.

    FAIL-CLOSED: dizin yok/okunamaz -> Olculemedi. JSON bozuk -> Olculemedi.
    id yok/bos/metin degil, ayni id iki kez, tanimlayici cakismasi -> Kirmizi.
    """
    if not os.path.isdir(kaynak_dizin):
        raise Olculemedi("kaynak dizin YOK ya da dizin degil: " + kaynak_dizin)
    try:
        girisler = sorted(os.listdir(kaynak_dizin))
    except OSError as e:
        raise Olculemedi("kaynak dizin okunamadi: " + kaynak_dizin + " (" + str(e) + ")")

    adlar = [g[:-5] for g in girisler if g.endswith(".json")]
    if not adlar:
        # Bos kaynak = "hicbir sari urun odenemez" demektir; sessizce bos artefakt URETME.
        raise Kirmizi("kaynak dizinde HIC .json sema yok: " + kaynak_dizin +
                      " — bos artefakt uretmek TUM sari seriyi sessizce odenemez yapardi")

    semalar = []
    idler = {}
    tanimlayicilar = {}
    hatalar = []
    for ad in adlar:
        yol = os.path.join(kaynak_dizin, ad + ".json")
        try:
            with open(yol, "r", encoding="utf-8") as f:
                sema = json.load(f)
        except (OSError, ValueError) as e:
            raise Olculemedi("sema okunamadi/ayristirilamadi: " + ad + ".json (" + str(e) + ")")
        if not isinstance(sema, dict):
            hatalar.append(ad + ": sema bir obje degil")
            continue
        sid = sema.get("id")
        if not isinstance(sid, str) or not sid.strip():
            hatalar.append(ad + ": sema `id` alani YOK/BOS/metin degil — Map anahtari "
                                "olusmaz, urun sessizce odenemez olur")
            continue
        if sid in idler:
            hatalar.append(sid + ": AYNI id iki semada (" + idler[sid] + ".json, " + ad +
                           ".json) — Map sessizce SON kaydi tutar, urun YANLIS semanin "
                           "matematigiyle fiyatlanirdi")
            continue
        t = _tanimlayici(ad)
        if t in tanimlayicilar:
            hatalar.append(ad + ": JS tanimlayici cakismasi (" + tanimlayicilar[t] +
                           ".json ile ayni '" + t + "') — bundle kurulamaz")
            continue
        idler[sid] = ad
        tanimlayicilar[t] = ad
        semalar.append((ad, sema))

    if hatalar:
        raise Kirmizi("bozuk sema kaydi: " + str(len(hatalar)) + "\n  " + "\n  ".join(hatalar))
    return semalar


def turet(semalar):
    """[(ad, sema)] -> shop/src/semalar.js icerigi (metin). Saf fonksiyon."""
    satirlar = [BASLIK.rstrip("\n"), ""]
    for ad, _ in semalar:
        satirlar.append('import ' + _tanimlayici(ad) + ' from "' + IMPORT_ONEK + ad + '.json";')
    satirlar.append("")
    satirlar.append("const HEPSI = [")
    for ad, _ in semalar:
        satirlar.append("  " + _tanimlayici(ad) + ",")
    satirlar.append("];")
    satirlar.append("")
    satirlar.append(GOVDE_YORUM)
    satirlar.append("export const SEMALAR = new Map(HEPSI.map((s) => [s.id, s]));")
    satirlar.append("")
    satirlar.append("export default SEMALAR;")
    satirlar.append("")
    return "\n".join(satirlar)


def _beklenen(kaynak_dizin):
    return turet(semalari_oku(kaynak_dizin))


def kapi(kaynak_dizin, artefakt_yolu, sessiz=False):
    """KAPI: artefakt kaynaktan turetilenle BIREBIR mi? Cikis kodu sozlesmesine uyar."""
    try:
        semalar = semalari_oku(kaynak_dizin)
    except Olculemedi as e:
        if not sessiz:
            print("SEMA BUNDLE KAPISI")
            print("  ⚠️ OLCULEMEDI: " + str(e))
            print("----------------------------------------------------------------------")
            print("SONUC: OLCULEMEDI ⚠️  — 'yesil' DEGIL (exit " + str(RC_OLCULEMEDI) + ")")
        return RC_OLCULEMEDI
    except Kirmizi as e:
        if not sessiz:
            print("SEMA BUNDLE KAPISI")
            print("  ❌ KAYNAK KABUL EDILEMEZ — artefakt URETILMEDI (fail-closed)")
            print("  " + str(e))
            print("----------------------------------------------------------------------")
            print("SONUC: KIRMIZI ❌  — once jenerator/urunler/ altindaki semayi duzelt.")
        return RC_KIRMIZI

    beklenen = turet(semalar)
    var_mi = os.path.exists(artefakt_yolu)
    mevcut = ""
    if var_mi:
        try:
            with open(artefakt_yolu, "r", encoding="utf-8") as f:
                mevcut = f.read()
        except OSError as e:
            if not sessiz:
                print("SEMA BUNDLE KAPISI")
                print("  ⚠️ OLCULEMEDI: artefakt okunamadi (" + str(e) + ")")
                print("SONUC: OLCULEMEDI ⚠️  — 'yesil' DEGIL (exit " + str(RC_OLCULEMEDI) + ")")
            return RC_OLCULEMEDI

    if mevcut == beklenen:
        if not sessiz:
            print("SEMA BUNDLE KAPISI")
            print("  kaynak    : " + os.path.relpath(kaynak_dizin, ROOT) + "/*.json")
            print("  artefakt  : " + os.path.relpath(artefakt_yolu, ROOT))
            print("  sema      : " + str(len(semalar)) +
                  "   (benzersiz id: " + str(len(set(s.get("id") for _, s in semalar))) + ")")
            print("----------------------------------------------------------------------")
            print("SONUC: YESIL ✅  — import listesi jenerator/urunler/ ile BIREBIR.")
        return RC_YESIL

    if not sessiz:
        beklenen_adlar = set(ad for ad, _ in semalar)
        mevcut_adlar = set(re.findall(re.escape(IMPORT_ONEK) + r"([A-Za-z0-9._-]+)\.json",
                                      mevcut))
        eksik = sorted(beklenen_adlar - mevcut_adlar)
        fazla = sorted(mevcut_adlar - beklenen_adlar)
        print("SEMA BUNDLE KAPISI")
        print("  ❌ ARTEFAKT BAYAT/ELLE DEGISTIRILMIS: " +
              os.path.relpath(artefakt_yolu, ROOT))
        if not var_mi:
            print("     (dosya YOK)")
        else:
            print("     listede EKSIK sema (dizinde VAR): " + (", ".join(eksik) if eksik else "-"))
            print("     listede FAZLA sema (dizinde YOK): " + (", ".join(fazla) if fazla else "-"))
            print("     satir sayisi: artefakt=" + str(len(mevcut.splitlines())) +
                  " beklenen=" + str(len(beklenen.splitlines())))
        print("----------------------------------------------------------------------")
        print("SONUC: KIRMIZI ❌  — COZUM: ISCIYE: python3 tools/sema-bundle-kapisi.py --yaz")
        print("  (artefakt ELLE duzenlenmez; jenerator/urunler/ TEK KAYNAK. Liste bayat")
        print("   kaldigi surece o sari urun kartla TAHSIL EDILEMEZ — kalem fail-closed 400")
        print("   ile WhatsApp'a duser.)")
    return RC_KIRMIZI


def yaz(kaynak_dizin, artefakt_yolu):
    try:
        semalar = semalari_oku(kaynak_dizin)
    except Olculemedi as e:
        print("SEMA BUNDLE: OLCULEMEDI — " + str(e))
        return RC_OLCULEMEDI
    except Kirmizi as e:
        print("SEMA BUNDLE: artefakt URETILMEDI (fail-closed) — " + str(e))
        return RC_KIRMIZI
    icerik = turet(semalar)
    onceki = ""
    if os.path.exists(artefakt_yolu):
        with open(artefakt_yolu, "r", encoding="utf-8") as f:
            onceki = f.read()
    if onceki == icerik:
        print("SEMA BUNDLE: artefakt zaten guncel (" +
              os.path.relpath(artefakt_yolu, ROOT) + ", " + str(len(semalar)) + " sema)")
        return RC_YESIL
    with open(artefakt_yolu, "w", encoding="utf-8") as f:
        f.write(icerik)
    print("SEMA BUNDLE: yazildi -> " + os.path.relpath(artefakt_yolu, ROOT) +
          " (" + str(len(semalar)) + " sema)")
    return RC_YESIL


# ---------------------------------------------------------------- kendini test
def _fikstur(gec, adlar=None):
    """Gercek kaynak dizinin KOPYASI + ondan uretilmis artefakt. (dizin, artefakt) doner."""
    dizin = os.path.join(gec, "urunler")
    shutil.copytree(KAYNAK_VARSAYILAN, dizin)
    if adlar is not None:
        for g in sorted(os.listdir(dizin)):
            if g.endswith(".json") and g[:-5] not in adlar:
                os.remove(os.path.join(dizin, g))
    art = os.path.join(gec, "semalar.js")
    with open(art, "w", encoding="utf-8") as f:
        f.write(turet(semalari_oku(dizin)))
    return dizin, art


def _ornek_sema(sid):
    return {"id": sid, "baslik": "Test", "tabanFiyatTL": 100, "tabanHacimMm3": 1000,
            "parametreler": [{"ad": "cap", "min": 5, "max": 50, "adim": 1, "varsayilan": 10}]}


def kendini_test():
    """POZITIF + NEGATIF vaka (tek yon = olu nobetci) + no-op mutasyon olcumu."""
    ham = ["SEMA BUNDLE KAPISI — KENDINI TEST"]
    kirmizi = 0

    def iddia(ad, gercek, beklenen):
        nonlocal kirmizi
        if gercek == beklenen:
            ham.append("    ✅ " + ad + " -> rc=" + str(gercek))
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + " -> rc=" + str(gercek) + " (beklenen " +
                       str(beklenen) + ")")

    with tempfile.TemporaryDirectory() as gec:
        # ---- (A) POZITIF: liste <-> dosya kumesi uyusuyor -> YESIL
        dizin, art = _fikstur(gec)
        n = len(semalari_oku(dizin))
        ham.append("  (A) POZITIF — kaynak " + str(n) + " sema")
        iddia("A1 liste == dizin", kapi(dizin, art, sessiz=True), RC_YESIL)

        # A2 YANLIS-POZITIF NOBETI: dizine .json OLMAYAN dosya konursa kapi YESIL kalmali.
        with open(os.path.join(dizin, "NOTLAR.md"), "w", encoding="utf-8") as f:
            f.write("# not\n")
        with open(os.path.join(dizin, "taslak.json.bak"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        iddia("A2 dizine .json OLMAYAN dosya eklendi (yanlis-pozitif nobeti)",
              kapi(dizin, art, sessiz=True), RC_YESIL)

        # A3 YANLIS-POZITIF: semanin ICERIGI degisti (fiyat/parametre) — liste degismez.
        hedef = os.path.join(dizin, sorted(os.listdir(dizin))[0])
        if hedef.endswith(".json"):
            with open(hedef, "r", encoding="utf-8") as f:
                j = json.load(f)
            j["tabanFiyatTL"] = (j.get("tabanFiyatTL") or 0) + 1
            with open(hedef, "w", encoding="utf-8") as f:
                json.dump(j, f, ensure_ascii=False)
        iddia("A3 sema ICERIGI (tabanFiyatTL) degisti (yanlis-pozitif nobeti)",
              kapi(dizin, art, sessiz=True), RC_YESIL)

        # A4 YANLIS-POZITIF: artefaktin SATIR SONU disinda hicbir sey degismedigi hal —
        # ayni icerik yeniden uretilince kapi yine yesil (uretim deterministik mi).
        with open(art, "w", encoding="utf-8") as f:
            f.write(turet(semalari_oku(dizin)))
        iddia("A4 uretim deterministik (ikinci uretim == birinci)",
              kapi(dizin, art, sessiz=True), RC_YESIL)

    with tempfile.TemporaryDirectory() as gec:
        # ---- (B) NEGATIF: her hal AYRI vaka
        ham.append("  (B) NEGATIF")
        dizin, art = _fikstur(gec)
        # B1 sema dosyasi EKLENDI, liste guncellenmedi -> KIRMIZI
        with open(os.path.join(dizin, "olcuye-ozel-yeni-aile.json"), "w", encoding="utf-8") as f:
            json.dump(_ornek_sema("olcuye-ozel-yeni-aile"), f, ensure_ascii=False)
        iddia("B1 sema EKLENDI, liste guncellenmedi", kapi(dizin, art, sessiz=True), RC_KIRMIZI)
        os.remove(os.path.join(dizin, "olcuye-ozel-yeni-aile.json"))

        # B2 liste FAZLA giris tasiyor (dosya silindi, liste ayni) -> KIRMIZI
        silinen = "olcuye-ozel-toka.json"
        os.remove(os.path.join(dizin, silinen))
        iddia("B2 sema SILINDI, liste fazla giris tasiyor",
              kapi(dizin, art, sessiz=True), RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B3 sema YENIDEN ADLANDIRILDI -> KIRMIZI (hem eksik hem fazla)
        os.rename(os.path.join(dizin, "olcuye-ozel-huni.json"),
                  os.path.join(dizin, "olcuye-ozel-huni-v2.json"))
        iddia("B3 sema YENIDEN ADLANDIRILDI", kapi(dizin, art, sessiz=True), RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B4 KAYNAK OKUNAMADI (dizin yok) -> OLCULEMEDI + sifir-disi
        iddia("B4 kaynak dizin YOK -> OLCULEMEDI",
              kapi(os.path.join(gec, "yok-boyle-dizin"), art, sessiz=True), RC_OLCULEMEDI)
        # B5 sema JSON'u BOZUK (ayristirilamaz) -> OLCULEMEDI + sifir-disi
        with open(os.path.join(dizin, "olcuye-ozel-rulman.json"), "w", encoding="utf-8") as f:
            f.write("{ bozuk json ")
        iddia("B5 sema JSON'u BOZUK -> OLCULEMEDI", kapi(dizin, art, sessiz=True),
              RC_OLCULEMEDI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B6 sema `id` alani YOK -> KIRMIZI (kayit sessizce erisilemez olurdu)
        yol = os.path.join(dizin, "olcuye-ozel-cetvel.json")
        with open(yol, "r", encoding="utf-8") as f:
            j = json.load(f)
        j.pop("id", None)
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False)
        iddia("B6 sema `id` alani YOK", kapi(dizin, art, sessiz=True), RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B7 IKI sema AYNI id -> KIRMIZI (Map sessizce son kaydi tutar = YANLIS FIYAT)
        yol = os.path.join(dizin, "olcuye-ozel-cetvel.json")
        with open(yol, "r", encoding="utf-8") as f:
            j = json.load(f)
        j["id"] = "olcuye-ozel-rulman"
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False)
        iddia("B7 IKI sema AYNI id (sessiz yanlis fiyat)", kapi(dizin, art, sessiz=True),
              RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B8 ARTEFAKT YOK -> KIRMIZI
        os.remove(art)
        iddia("B8 artefakt dosyasi YOK", kapi(dizin, art, sessiz=True), RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        dizin, art = _fikstur(gec)
        # B9 kaynak dizinde HIC sema yok -> KIRMIZI (bos artefakt URETILMEZ)
        for g in os.listdir(dizin):
            if g.endswith(".json"):
                os.remove(os.path.join(dizin, g))
        iddia("B9 kaynakta HIC sema yok (bos artefakt uretilmez)",
              kapi(dizin, art, sessiz=True), RC_KIRMIZI)

    with tempfile.TemporaryDirectory() as gec:
        # ---- (C) URETICI KOLU: --yaz iki yonde de dogru davranmali
        ham.append("  (C) URETICI (--yaz)")
        dizin, art = _fikstur(gec)
        iddia("C1 --yaz zaten guncel", yaz(dizin, art), RC_YESIL)
        with open(os.path.join(dizin, "olcuye-ozel-yeni-aile.json"), "w", encoding="utf-8") as f:
            json.dump(_ornek_sema("olcuye-ozel-yeni-aile"), f, ensure_ascii=False)
        iddia("C2 --yaz drift'i onarir", yaz(dizin, art), RC_YESIL)
        iddia("C3 onarim sonrasi kapi YESIL", kapi(dizin, art, sessiz=True), RC_YESIL)
        # C4 bozuk kaynakta --yaz artefakti EZMEMELI
        with open(art, "r", encoding="utf-8") as f:
            once = f.read()
        yol = os.path.join(dizin, "olcuye-ozel-yeni-aile.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"baslik": "id yok"}, f, ensure_ascii=False)
        rc = yaz(dizin, art)
        with open(art, "r", encoding="utf-8") as f:
            sonra = f.read()
        iddia("C4 bozuk kaynakta --yaz REDDEDER", rc, RC_KIRMIZI)
        iddia("C4b bozuk kaynakta artefakt EZILMEDI", once == sonra, True)

    # ---- (D) NO-OP MUTASYONU: her yeni iddiayi etkisizlestiren mutant KIRMIZI yanmali.
    ham.append("  (D) NO-OP MUTASYONU (iddia yuk tasiyor mu)")
    with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
        oz_kaynak = f.read()
    # 🔴 CAPALAR COK SATIRLI: tek satirlik capa bu listenin KENDI govdesinde de gecerdi
    # (count != 1 -> "capa yok/cok"). Kaynakta GERCEK satir sonu var, bu listede `\n`
    # KACISI var -> bayt dizisi ayrisir, capa tektir.
    mutasyonlar = [
        ("MU1 id dogrulamasi NO-OP (id yok/bos kabul edilir)",
         '        sid = sema.get("id")\n'
         '        if not isinstance(sid, str) or not sid.strip():',
         '        sid = sema.get("id")\n'
         '        if False:'),
        ("MU2 mukerrer id dogrulamasi NO-OP (Map sessizce son kaydi tutar)",
         '        if sid in idler:\n'
         '            hatalar.append(sid + ": AYNI id iki semada ("',
         '        if False:\n'
         '            hatalar.append(sid + ": AYNI id iki semada ("'),
        ("MU3 bos kaynak kabul edilir (bos artefakt uretilir)",
         '    if not adlar:\n'
         '        # Bos kaynak',
         '    if False:\n'
         '        # Bos kaynak'),
    ]
    # Her mutant, KENDI iddiasinin fikstruyle olculur: mutant SESSIZ gecmeli (=iddia yuk
    # tasiyordu). Mutant hala KIRMIZI verirse iddia OLU demektir.
    mut_kacan = 0
    for ad, capa, yerine in mutasyonlar:
        if oz_kaynak.count(capa) != 1:
            kirmizi += 1
            mut_kacan += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK: " + ad)
            continue
        ns = {"__name__": "sbk_mutant", "__file__": os.path.abspath(__file__)}
        exec(compile(oz_kaynak.replace(capa, yerine), "<sbk-mutant>", "exec"), ns)
        with tempfile.TemporaryDirectory() as gec:
            dizin = os.path.join(gec, "urunler")
            shutil.copytree(KAYNAK_VARSAYILAN, dizin)
            if ad.startswith("MU1"):
                yol = os.path.join(dizin, "olcuye-ozel-cetvel.json")
                with open(yol, "r", encoding="utf-8") as f:
                    j = json.load(f)
                j.pop("id", None)
                with open(yol, "w", encoding="utf-8") as f:
                    json.dump(j, f, ensure_ascii=False)
            elif ad.startswith("MU2"):
                yol = os.path.join(dizin, "olcuye-ozel-cetvel.json")
                with open(yol, "r", encoding="utf-8") as f:
                    j = json.load(f)
                j["id"] = "olcuye-ozel-rulman"
                with open(yol, "w", encoding="utf-8") as f:
                    json.dump(j, f, ensure_ascii=False)
            else:
                for g in os.listdir(dizin):
                    if g.endswith(".json"):
                        os.remove(os.path.join(dizin, g))
            try:
                ns["semalari_oku"](dizin)
                ham.append("    ✅ " + ad + " -> mutant SESSIZ gecti = iddia YUK TASIYOR")
            except Exception as e:  # noqa: BLE001 — mutantin hangi sinifla patladigi onemsiz
                if isinstance(e, (ns["Kirmizi"], ns["Olculemedi"])):
                    mut_kacan += 1
                    kirmizi += 1
                    ham.append("    ❌ OLU IDDIA: " + ad + " -> mutant da reddetti")
                else:
                    ham.append("    ✅ " + ad + " -> mutant baska yoldan patladi (" +
                               type(e).__name__ + ") = iddia yuk tasiyor")
    ham.append("  (D) " + str(len(mutasyonlar)) + " mutant denendi, " + str(mut_kacan) +
               " tanesi olcumsuz kaldi (0 olmali)")

    print("\n".join(ham))
    print("----------------------------------------------------------------------")
    print("SONUC: YESIL ✅ (kendini test)" if kirmizi == 0
          else "SONUC: KIRMIZI ❌ — " + str(kirmizi) + " iddia kaldi")
    return RC_YESIL if kirmizi == 0 else RC_KIRMIZI


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yaz", action="store_true", help="artefakti uret (tek bakim komutu)")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="pozitif + negatif vaka + no-op mutasyon olcumu")
    ap.add_argument("--kaynak", default=KAYNAK_VARSAYILAN)
    ap.add_argument("--dosya", default=ARTEFAKT_VARSAYILAN)
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    if a.yaz:
        return yaz(a.kaynak, a.dosya)
    return kapi(a.kaynak, a.dosya)


if __name__ == "__main__":
    sys.exit(main())
