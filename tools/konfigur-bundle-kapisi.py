#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR BUNDLE KAPISI — shop/src/konfigurlar.js'i urunler.json'dan TURETIR + DRIFT'i bloklar.

NEDEN VAR (olculmus is kaybi, 29 Tem):
  Worker'in konfigur ("olcuye ozel dekor") fiyatini hesaplayabilmesi icin urunun konfigur
  objesine (boy araligi + capalar + malzeme katsayilari) ihtiyaci var. Bu veri urunler.json
  ICINDE yasar; tum urunler.json'u Worker bundle'ina katmak (13k+ urun, ~12 MB) script
  boyutunu patlatir. Bu yuzden shop/src/konfigurlar.js uzun sure ELLE BAKIMLI bir AYNA'ydi:
  yeni konfigurlu urun eklenince ayna elle guncellenene kadar urun kartla ODENEMIYORDU
  (fail-closed 400 -> WhatsApp). Bugun bu iki kez is cikardi.

COZUM: ayna artik ELLE YAZILMAZ, urunler.json'dan TURETILIR (tek kaynak). Bu dosya hem
  URETICI (--yaz) hem de KAPI'dir (varsayilan: karsilastir, sapma varsa exit 1).

KAPSAM — DAR VE JETON EKSENINDE (kapi-kapsam-eksen-secimi dersi):
  Kapi YALNIZ "urunler.json'daki konfigur alanlarindan turetilen icerik" ile artefakti
  karsilastirir. Konfigursuz urun eklemek/silmek, fiyat/aciklama/gorsel duzenlemek, CSS/HTML
  degistirmek, urun sirasini degistirmek, konfigur objesi icindeki ANAHTAR SIRASINI
  degistirmek turetilen ciktiyi DEGISTIRMEZ -> kapi YESIL kalir (yanlis-pozitif olcumu:
  --kendini-test, 9 senaryo). Yani rutin urun/CSS isi TUM EKIBIN yayinini durdurmaz.

FAIL-CLOSED:
  * Konfigur objesi bozuk/eksik alanli ise (boyutMm/hacim/fiyatCapalari/malzemeler) URETIM
    REDDEDILIR (exit 1) — yarim/bozuk artefakt SHIP EDILMEZ. Worker tarafinda eksik veri
    zaten 400 uretir (shop/src/konfigur.js "konfigur-yok"); bu kapi o hali bundle'a hic
    sokmaz.
  * Sapma halinde kapi cikti verir ve exit 1 — sessiz gecis yolu YOKTUR.

KULLANIM:
    python3 tools/konfigur-bundle-kapisi.py                # KAPI (CI): sapma -> exit 1
    python3 tools/konfigur-bundle-kapisi.py --yaz          # artefakti URET (tek bakim komutu)
    python3 tools/konfigur-bundle-kapisi.py --kendini-test # kapinin kendi kirmizi-mutasyon +
                                                           # yanlis-pozitif olcumu
    python3 tools/konfigur-bundle-kapisi.py --urunler X --dosya Y   # test/fikstur yollari
"""
import argparse
import json
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
URUNLER_VARSAYILAN = os.path.join(ROOT, "urunler.json")
ARTEFAKT_VARSAYILAN = os.path.join(ROOT, "shop", "src", "konfigurlar.js")

BASLIK = """/**
 * URETILMIS DOSYA — ELLE DUZENLEME (elle yapilan degisiklik ilk uretimde KAYBOLUR).
 *
 * KAYNAK: urunler.json — "konfigur" alani tasiyan urunler (TEK KAYNAK).
 * URET  : python3 tools/konfigur-bundle-kapisi.py --yaz
 * KAPI  : python3 tools/konfigur-bundle-kapisi.py   (deploy.yml'de BLOKLAYICI; artefakt
 *         bayatsa CI KIRMIZI yanar -> "urun eklendi, ayna guncellenmedi" penceresi kapali)
 *
 * NEDEN AYRI ARTEFAKT: tum urunler.json (13k+ urun) Worker bundle'ina katilamaz (script
 * boyutu). Yalniz konfigur objeleri turetilir. Anahtar = urunler.json'daki kebab-id;
 * eslesmezse index.js konfigur kolu urunu GORMEZ -> konfigur-beklenen.js fail-closed kapisi
 * kalemi 400'e dusurur (sessizce sabit fiyata DUSMEZ).
 *
 * Konfigur verisi public (matematik + aralik + renk/malzeme); sir icermez.
 */
"""

ZORUNLU_ALANLAR = ("boyutMm", "hacim", "fiyatCapalari", "malzemeler")

# Bos/null konfigur halinde basilan COZUM metni + FAIL-CLOSED gerekcesi.
#
# NEDEN FAIL-CLOSED (bu kapi CI'da BLOKLAYICI; sahte kirmizi TUM EKIBIN yayinini durdurur —
# karar bilerek bu bedele gore verildi):
#   1. YANLIS-POZITIF BEDELI OLCULDU = 0. Gercek katalogda (14.966 urun, 30 Tem) "konfigur"
#      anahtari tasiyan 16 urunun 16'si DOLU; bos/null olan 0 kayit var. Yani bugun bu kural
#      hicbir mesru katalog halini kirmizi yakmaz — kapiyi ancak BIRISI urunler.json'a
#      `"konfigur": {}` / `"konfigur": null` YAZARSA tetiklenir.
#   2. O YAZIM HICBIR ZAMAN MESRU DEGIL. Urun konfigurlu degilse anahtar HIC KONMAZ (katalogun
#      geri kalani boyle); konfigurlu ise obje dolu olmak zorunda. Bos deger "konfigurlu ama
#      verisiz" demektir — sitede konfigurator karti gorunur, Worker fiyatlayamaz.
#   3. TUTARLILIK: `{"boyutMm": ...}` diye YARIM yazilmis konfigur zaten fail-closed
#      (`_sema_dogrula` -> "eksik alan"). `{}` = TUM alanlari eksik olan hal; onun daha
#      GEVSEK (sessiz) bir yoldan gecmesi tasarim degil, kusurdu.
#   4. FAIL-OPEN'IN BEDELI SESSIZ VE PARALI: urun canlida kalir, musteri konfiguratoru kullanir,
#      odeme aninda 400 alir, kalem WhatsApp'a duser. Kimse bakmadikca gorunmez.
#   Kirmizi yandiginda cozum TEK SATIRLIK ve mesajda yazili -> ekibi dakikalarca degil
#   saniyelerce durdurur.
_BOS_KONFIGUR_COZUM = (
    "  COZUM (bos/null konfigur icin): urun KONFIGURLU ise `konfigur` objesini doldur\n"
    "  (boyutMm/hacim/fiyatCapalari/malzemeler); konfigurlu DEGILSE `konfigur` anahtarini\n"
    "  urunden TAMAMEN kaldir. Bos birakma — bos deger urunu sessizce odenemez yapar."
)


def _sema_dogrula(urun_id, konf):
    """Konfigur objesinin Worker'in fiyat cekirdeginin BEKLEDIGI alanlari tasidigini dogrular.
    Eksik/bozuksa hata metni doner (fail-closed: bozuk artefakt uretilmez)."""
    if not isinstance(konf, dict):
        return "konfigur bir obje degil"
    eksik = [a for a in ZORUNLU_ALANLAR if a not in konf]
    if eksik:
        return "eksik alan: " + ",".join(eksik)
    b = konf.get("boyutMm")
    if not isinstance(b, dict) or not all(
            isinstance(b.get(k), (int, float)) for k in ("min", "max", "adim", "varsayilan")):
        return "boyutMm min/max/adim/varsayilan sayisal degil"
    h = konf.get("hacim")
    if not isinstance(h, dict) or not all(
            isinstance(h.get(k), (int, float)) for k in ("refYukseklikMm", "refHacimCm3")):
        return "hacim refYukseklikMm/refHacimCm3 sayisal degil"
    c = konf.get("fiyatCapalari")
    if (not isinstance(c, list) or len(c) != 2 or
            not all(isinstance(p, list) and len(p) == 2 and
                    all(isinstance(x, (int, float)) for x in p) for p in c)):
        return "fiyatCapalari [[boyMm,TL],[boyMm,TL]] bicimde degil"
    m = konf.get("malzemeler")
    if (not isinstance(m, list) or not m or
            not all(isinstance(x, dict) and isinstance(x.get("ad"), str) and
                    isinstance(x.get("katsayi"), (int, float)) and x.get("katsayi") > 0
                    for x in m)):
        return "malzemeler [{ad,katsayi>0}] bicimde degil"
    return ""


def konfigur_haritasi(urunler):
    """urunler listesinden {id: konfigur} (id'ye gore SIRALI) cikarir. Bozuk sema -> SystemExit.

    SIRALAMA id'ye gore: urunler.json'da yeni urun dizinin BASINA eklenir; sira eksenine
    bagli bir artefakt her urun eklemesinde degisirdi (gereksiz drift). id sirasi kararlidir.
    """
    harita = {}
    hatalar = []
    for u in urunler:
        if not isinstance(u, dict):
            continue
        # 🔴 ANAHTAR YOK vs ANAHTAR BOS — AYRI SINIFLAR (30 Tem, S1):
        #   * "konfigur" anahtari YOK  -> urun konfigurlu DEGIL. Katalogun ~%99,9'u boyle;
        #     SESSIZ atlanir (normal hal, gurultu uretmez).
        #   * anahtar VAR ama deger BOS/NULL ({} / null / [] / "" / 0 / false) -> yazan kisi
        #     KONFIGURLU urun kastetmis ama veri bos. Eski kod bunu `not u.get("konfigur")`
        #     ile ANAHTARSIZ urunle AYNI kefeye koyup SESSIZCE dusuruyordu: urun sitede
        #     konfigurator kartiyla gorunur, Worker bundle'inda YOKTUR -> odeme aninda
        #     fail-closed 400 -> kalem WhatsApp'a duser = SESSIZ GELIR KAYBI, tek uyari yok.
        #     Artik bu hal `_sema_dogrula`nin "eksik alan" haliyle AYNI kefeye girer:
        #     GURULTULU + FAIL-CLOSED (gerekce icin asagidaki _BOS_KONFIGUR_ACIKLAMA).
        if "konfigur" not in u:
            continue
        if not u["konfigur"]:
            uid_bos = u.get("id")
            hatalar.append((uid_bos if isinstance(uid_bos, str) and uid_bos else "<id YOK>") +
                           ": konfigur alani VAR ama BOS/NULL (" +
                           json.dumps(u["konfigur"], ensure_ascii=False) + ") — " +
                           "urun bundle'a GIRMEZ, odeme aninda 400 yerdi")
            continue
        uid = u.get("id")
        if not isinstance(uid, str) or not uid:
            hatalar.append("id'siz konfigurlu urun kaydi")
            continue
        if uid in harita:
            hatalar.append(uid + ": ayni id iki kez")
            continue
        sema_hata = _sema_dogrula(uid, u["konfigur"])
        if sema_hata:
            hatalar.append(uid + ": " + sema_hata)
            continue
        harita[uid] = u["konfigur"]
    if hatalar:
        sys.exit("KONFIGUR BUNDLE: bozuk konfigur verisi — artefakt URETILMEDI (fail-closed)\n"
                 "  bozuk kayit: " + str(len(hatalar)) + "\n  "
                 + "\n  ".join(hatalar) + "\n" + _BOS_KONFIGUR_COZUM)
    return dict(sorted(harita.items()))


def _sayi_normalize(o):
    """TAM SAYI DEGERLI float'i int'e cevirir (1.0 -> 1). SEBEP: urunler.json'da katsayi bazen
    `1.0` bazen `1` yazilir; ikisi JS'te AYNI degerdir (IEEE754 double) ama ham dump'ta farkli
    METIN uretir -> artefakt fiyat DEGISMEDIGI halde sapar ve kapi gereksiz yere kirmizi yanardi
    (yanlis-pozitif). Normalizasyon YALNIZ tam-sayi-degerli float'a dokunur; 213.12 gibi degerler
    aynen kalir, deger KAYBI olmaz."""
    if isinstance(o, dict):
        return {k: _sayi_normalize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_sayi_normalize(v) for v in o]
    if isinstance(o, bool):
        return o
    if isinstance(o, float) and o.is_integer():
        return int(o)
    return o


def turet(urunler):
    """urunler listesinden shop/src/konfigurlar.js icerigini (metin) uretir. Saf fonksiyon."""
    harita = _sayi_normalize(konfigur_haritasi(urunler))
    govde = json.dumps(harita, ensure_ascii=False, sort_keys=True, indent=2)
    satirlar = [BASLIK, "",
                "/** id -> konfigur objesi (urunler.json'dan TURETILMIS; id'ye gore sirali). */",
                "const VERI = " + govde + ";", "",
                "export const KONFIGURLAR = new Map(Object.entries(VERI));", "",
                "export default KONFIGURLAR;", ""]
    return "\n".join(satirlar)


def _urunleri_oku(yol):
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    if not isinstance(veri, list):
        sys.exit("KONFIGUR BUNDLE: " + yol + " bir dizi degil")
    return veri


def kapi(urunler_yolu, artefakt_yolu, sessiz=False):
    """KAPI: artefakt urunler.json'dan turetilenle BIREBIR mi? Degilse 1 doner."""
    beklenen = turet(_urunleri_oku(urunler_yolu))
    var_mi = os.path.exists(artefakt_yolu)
    mevcut = ""
    if var_mi:
        with open(artefakt_yolu, "r", encoding="utf-8") as f:
            mevcut = f.read()
    if mevcut == beklenen:
        if not sessiz:
            ham = _urunleri_oku(urunler_yolu)
            adet = len(konfigur_haritasi(ham))
            # GURULTU (S1): "anahtari olan" ile "bundle'a giren" sayilari EKRANDA yan yana.
            # Ikisi esit degilse bir kayit sessizce dusmus demektir; fail-closed sayesinde o
            # hale hic gelinmez ama sayi yine de BASILIR — sessiz dusme bir daha gorunmez olmasin.
            anahtarli = len([u for u in ham if isinstance(u, dict) and "konfigur" in u])
            print("KONFIGUR BUNDLE KAPISI")
            print("  kaynak    : " + os.path.relpath(urunler_yolu, ROOT))
            print("  artefakt  : " + os.path.relpath(artefakt_yolu, ROOT))
            print("  konfigurlu urun: " + str(adet) +
                  "   (konfigur anahtarli kayit: " + str(anahtarli) +
                  ", dusen: " + str(anahtarli - adet) + ")")
            print("----------------------------------------------------------------------")
            print("SONUC: YESIL ✅  — artefakt urunler.json'dan turetilenle BIREBIR.")
        return 0
    if not sessiz:
        bek = beklenen.splitlines()
        mev = mevcut.splitlines()
        print("KONFIGUR BUNDLE KAPISI")
        print("  ❌ ARTEFAKT BAYAT/ELLE DEGISTIRILMIS: " +
              os.path.relpath(artefakt_yolu, ROOT))
        if not var_mi:
            print("     (dosya YOK)")
        else:
            beklenen_idler = set(konfigur_haritasi(_urunleri_oku(urunler_yolu)).keys())
            mevcut_idler = set()
            # 🔴 SADECE UST DUZEY anahtarlar (girinti TAM 2 boşluk) urun id'sidir. Eski kod
            # girintiye bakmadigi icin konfigur objesinin ICINDEKI anahtarlari (boyutMm,
            # hacim, renkGorselIndeks ...) "artefaktta FAZLA id" diye raporluyordu — kapi
            # tam da en cok konusmasi gereken anda YANILTICI konusuyordu (olculdu 30 Tem:
            # tek urun eksikken teshis 3 sahte "fazla id" basiyordu).
            for s in mev:
                if not s.startswith('  "') or s.startswith('   '):
                    continue
                if s.rstrip().endswith("{"):
                    mevcut_idler.add(s.split('"')[1])
            eksik = sorted(beklenen_idler - mevcut_idler)
            fazla = sorted(mevcut_idler - beklenen_idler)
            print("     artefaktta EKSIK id: " + (", ".join(eksik) if eksik else "-"))
            print("     artefaktta FAZLA id: " + (", ".join(fazla) if fazla else "-"))
            print("     satir sayisi: artefakt=" + str(len(mev)) + " beklenen=" + str(len(bek)))
        print("----------------------------------------------------------------------")
        print("SONUC: KIRMIZI ❌  — COZUM: python3 tools/konfigur-bundle-kapisi.py --yaz")
        print("  (artefakt ELLE duzenlenmez; urunler.json TEK KAYNAK. Worker'in yeni urunu")
        print("   kartla tahsil edebilmesi icin artefakt uretilip Worker yeniden yayinlanir;")
        print("   yayinlanana kadar kalem fail-closed 400 ile WhatsApp'a duser.)")
    return 1


def yaz(urunler_yolu, artefakt_yolu):
    icerik = turet(_urunleri_oku(urunler_yolu))
    onceki = ""
    if os.path.exists(artefakt_yolu):
        with open(artefakt_yolu, "r", encoding="utf-8") as f:
            onceki = f.read()
    if onceki == icerik:
        print("KONFIGUR BUNDLE: artefakt zaten guncel (" +
              os.path.relpath(artefakt_yolu, ROOT) + ")")
        return 0
    with open(artefakt_yolu, "w", encoding="utf-8") as f:
        f.write(icerik)
    print("KONFIGUR BUNDLE: yazildi -> " + os.path.relpath(artefakt_yolu, ROOT) +
          " (" + str(len(konfigur_haritasi(_urunleri_oku(urunler_yolu)))) + " konfigurlu urun)")
    return 0


# ---------------------------------------------------------------- kendini test
def _ornek_konfigur():
    return {
        "renkler": ["Siyah", "Beyaz", "Gri"],
        "renkGorselIndeks": {"Gri": 0, "Siyah": 1, "Beyaz": 2},
        "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150, "etiket": "Yükseklik"},
        "hacim": {"refYukseklikMm": 150, "refHacimCm3": 213.12},
        "fiyatCapalari": [[60, 500], [300, 2500]],
        "malzemeler": [{"ad": "PLA", "katsayi": 1.0}, {"ad": "PETG", "katsayi": 1.3}],
        "varsayilanMalzeme": "PLA",
    }


def kendini_test():
    """Kapinin KENDI kabulu: (A) 9 yanlis-pozitif senaryosu YESIL kalmali, (B) gercek drift
    KIRMIZI yanmali, (C) CLI yolu (dosya karsilastirmasi) iki yonde de dogru cikis kodu
    vermeli, (D) bozuk sema uretimi REDDETMELI."""
    ham = []
    kirmizi = 0
    urunler = _urunleri_oku(URUNLER_VARSAYILAN)
    taban = turet(urunler)
    konfigurlu = [u for u in urunler if isinstance(u, dict) and u.get("konfigur")]
    ham.append("KONFIGUR BUNDLE KAPISI — KENDINI TEST")
    ham.append("  katalog=" + str(len(urunler)) + " urun; konfigurlu=" + str(len(konfigurlu)))

    # ---- (A) YANLIS-POZITIF SENARYOLARI: turetilen icerik DEGISMEMELI (kapi YESIL kalir).
    def kopya():
        return json.loads(json.dumps(urunler))

    senaryolar = []

    s = kopya()
    s.insert(0, {"id": "yeni-sira-disi-urun", "kategori": "Otomobil", "baslik": "Yeni",
                 "fiyat": "850 TL", "gorseller": []})
    senaryolar.append(("1 konfigursuz YENI urun dizinin basina eklendi", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and not u.get("konfigur"):
            u["fiyat"] = "999 TL"
            break
    senaryolar.append(("2 konfigursuz urunun FIYATI degisti", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and not u.get("konfigur"):
            u["aciklama"] = (u.get("aciklama") or "") + " ek cumle."
            break
    senaryolar.append(("3 konfigursuz urunun ACIKLAMASI degisti", s))

    s = kopya()
    s.reverse()
    senaryolar.append(("4 TUM katalog sirasi tersine cevrildi", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and u.get("konfigur"):
            u["konfigur"] = dict(reversed(list(u["konfigur"].items())))
            break
    senaryolar.append(("5 konfigur objesinin ANAHTAR SIRASI degisti", s))

    s = kopya()
    silindi = False
    for i, u in enumerate(s):
        if isinstance(u, dict) and not u.get("konfigur") and not u.get("parametrik"):
            del s[i]
            silindi = True
            break
    senaryolar.append(("6 konfigursuz bir urun SILINDI" + ("" if silindi else " (bulunamadi)"), s))

    s = kopya()
    s.insert(0, {"id": "yeni-parametrik-sari", "kategori": "Jeneratör", "baslik": "Sari",
                 "fiyat": "", "parametrik": True, "gorseller": []})
    senaryolar.append(("7 PARAMETRIK (sari) urun eklendi", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and u.get("konfigur"):
            u["baslik"] = (u.get("baslik") or "") + " (yeni gorsel)"
            u["gorseller"] = ["https://media.pruvo3d.com/urunler/degisti-1.jpg"]
            break
    senaryolar.append(("8 KONFIGURLU urunun konfigur-DISI alani (baslik/gorsel) degisti", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and not u.get("konfigur"):
            u["marka"] = ["Audi"]
            u["kategori"] = "Otomobil"
            break
    senaryolar.append(("9 konfigursuz urunun MARKA/KATEGORI alani degisti", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and u.get("konfigur"):
            # 1.0 -> 1 (ayni IEEE754 degeri, farkli yazim): ornegin katalog bir arac tarafindan
            # yeniden yazildiginda olur; fiyat DEGISMEZ -> kapi yanmamali.
            u["konfigur"]["malzemeler"] = [
                {"ad": m["ad"], "katsayi": int(m["katsayi"]) if float(m["katsayi"]).is_integer()
                 else m["katsayi"]} for m in u["konfigur"]["malzemeler"]]
    senaryolar.append(("10 sayi YAZIMI degisti (katsayi 1.0 -> 1, ayni deger)", s))

    yp = 0
    for ad, veri in senaryolar:
        ayni = turet(veri) == taban
        if not ayni:
            kirmizi += 1
            yp += 1
            ham.append("    ❌ YANLIS-POZITIF: " + ad + " -> turetilen icerik DEGISTI")
        else:
            ham.append("    ✅ " + ad + " -> turetilen icerik AYNI (kapi yesil kalir)")
    ham.append("  (A) yanlis-pozitif senaryosu: " + str(len(senaryolar)) + " denendi, " +
               str(yp) + " tanesi kapiyi yakti (0 olmali)")

    # ---- (B) KIRMIZI MUTASYON: gercek drift YAKALANMALI.
    mutantlar = []
    s = kopya()
    yeni = {"id": "ejderha-serit-dekoratif-figur", "kategori": "Skan Art", "baslik": "Ejderha",
            "fiyat": "500 TL", "gorseller": [], "konfigur": _ornek_konfigur()}
    s.insert(0, yeni)
    mutantlar.append(("M1 YENI konfigurlu urun eklendi (ayna guncellenmedi)", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and u.get("konfigur"):
            u["konfigur"]["fiyatCapalari"] = [[60, 700], [300, 2500]]
            break
    mutantlar.append(("M2 bir urunun FIYAT CAPASI degisti", s))

    s = kopya()
    for i, u in enumerate(s):
        if isinstance(u, dict) and u.get("konfigur"):
            del s[i]
            break
    mutantlar.append(("M3 konfigurlu bir urun SILINDI", s))

    s = kopya()
    for u in s:
        if isinstance(u, dict) and u.get("konfigur"):
            u["konfigur"]["malzemeler"] = [{"ad": "PLA", "katsayi": 1.0}]
            break
    mutantlar.append(("M4 bir urunun MALZEME listesi kisaldi", s))

    yakalanmayan = 0
    for ad, veri in mutantlar:
        if turet(veri) == taban:
            kirmizi += 1
            yakalanmayan += 1
            ham.append("    ❌ OLU KAPI: " + ad + " -> turetilen icerik DEGISMEDI")
        else:
            ham.append("    ✅ " + ad + " -> turetilen icerik DEGISTI (kapi kirmizi yanar)")
    ham.append("  (B) kirmizi-mutasyon: " + str(len(mutantlar)) + " denendi, " +
               str(yakalanmayan) + " tanesi kacti (0 olmali)")

    # ---- (C) CLI yolu: gercek dosya karsilastirmasi iki yonde de dogru cikis kodu versin.
    with tempfile.TemporaryDirectory() as gec:
        mini = os.path.join(gec, "urunler-mini.json")
        art = os.path.join(gec, "konfigurlar.js")
        with open(mini, "w", encoding="utf-8") as f:
            json.dump(konfigurlu, f, ensure_ascii=False)
        rc_yaz = yaz(mini, art)
        rc_es = kapi(mini, art, sessiz=True)
        genis = json.loads(json.dumps(konfigurlu))
        genis.insert(0, yeni)
        mini2 = os.path.join(gec, "urunler-mini-2.json")
        with open(mini2, "w", encoding="utf-8") as f:
            json.dump(genis, f, ensure_ascii=False)
        rc_drift = kapi(mini2, art, sessiz=True)
        rc_yok = kapi(mini, os.path.join(gec, "yok.js"), sessiz=True)
        ham.append("  (C) CLI: --yaz rc=" + str(rc_yaz) + " (0 olmali); esit rc=" + str(rc_es) +
                   " (0 olmali); DRIFT rc=" + str(rc_drift) + " (1 olmali); dosya-YOK rc=" +
                   str(rc_yok) + " (1 olmali)")
        if rc_yaz != 0 or rc_es != 0 or rc_drift != 1 or rc_yok != 1:
            kirmizi += 1
            ham.append("    ❌ CLI cikis kodlari beklenenle uyusmuyor")

    # ---- (D) FAIL-CLOSED: bozuk sema uretimi REDDETMELI (yarim artefakt ship edilmesin).
    bozuk_vaka = [
        ("hacim alani silinmis", lambda k: k.pop("hacim", None)),
        ("fiyatCapalari tek capaya inmis", lambda k: k.__setitem__("fiyatCapalari", [[60, 500]])),
        ("malzeme katsayisi 0", lambda k: k.__setitem__("malzemeler", [{"ad": "PLA", "katsayi": 0}])),
        ("boyutMm.max metin olmus", lambda k: k["boyutMm"].__setitem__("max", "300")),
    ]
    reddedilmeyen = 0
    for ad, boz in bozuk_vaka:
        s = kopya()
        for u in s:
            if isinstance(u, dict) and u.get("konfigur"):
                boz(u["konfigur"])
                break
        try:
            turet(s)
            reddedilmeyen += 1
            kirmizi += 1
            ham.append("    ❌ FAIL-OPEN: bozuk sema URETILDI — " + ad)
        except SystemExit:
            ham.append("    ✅ bozuk sema REDDEDILDI — " + ad)
    ham.append("  (D) bozuk-sema: " + str(len(bozuk_vaka)) + " denendi, " +
               str(reddedilmeyen) + " tanesi uretildi (0 olmali)")

    # ---- (E) BOS/NULL KONFIGUR (S1): anahtar VAR ama deger BOS -> GURULTULU + FAIL-CLOSED.
    # Eski kod bunu ANAHTARSIZ urunle ayni kefeye koyup SESSIZCE dusuruyordu (urun canlida
    # konfigurator kartiyla kalir, odeme aninda 400 yer = sessiz gelir kaybi).
    bos_vaka = [("bos obje {}", {}), ("null", None), ("bos dizi []", []),
                ("bos metin \"\"", ""), ("sifir 0", 0), ("false", False)]
    bos_kacan = 0
    for ad, deger in bos_vaka:
        s = kopya()
        s.insert(0, {"id": "bos-konfigur-vakasi", "kategori": "Skan Art", "baslik": "Bos",
                     "fiyat": "500 TL", "gorseller": [], "konfigur": deger})
        try:
            turet(s)
            bos_kacan += 1
            kirmizi += 1
            ham.append("    ❌ SESSIZ DUSTU: konfigur=" + ad + " -> urun bundle'a girmedi, "
                       "kapi hic konusmadi")
        except SystemExit as e:
            metin = str(e)
            # GURULTU SARTI: mesaj hem SAYIYI hem ID'yi soylemeli (yoksa "bir yerde bir sey
            # bozuk" der, kimse bulamaz).
            if "bos-konfigur-vakasi" in metin and "bozuk kayit: 1" in metin:
                ham.append("    ✅ konfigur=" + ad + " -> REDDEDILDI + id/sayi RAPORLANDI")
            else:
                bos_kacan += 1
                kirmizi += 1
                ham.append("    ❌ reddedildi ama GURULTU EKSIK (id/sayi yok) — konfigur=" + ad)
    # E-yanlis-pozitif: konfigur ANAHTARI OLMAYAN urun sessizce atlanmali (katalogun ~%99,9'u).
    s = kopya()
    s.insert(0, {"id": "anahtarsiz-normal-urun", "kategori": "Otomobil", "baslik": "Normal",
                 "fiyat": "850 TL", "gorseller": []})
    try:
        anahtarsiz_ok = turet(s) == taban
    except SystemExit:
        anahtarsiz_ok = False
    if not anahtarsiz_ok:
        kirmizi += 1
        ham.append("    ❌ YANLIS-POZITIF: konfigur ANAHTARI OLMAYAN urun kapiyi yakti")
    else:
        ham.append("    ✅ konfigur anahtari OLMAYAN urun sessizce atlandi (yanlis-pozitif yok)")
    ham.append("  (E) bos/null konfigur: " + str(len(bos_vaka)) + " denendi, " +
               str(bos_kacan) + " tanesi sessizce dustu (0 olmali)")

    # ---- (E-MUT) MUTASYON: (E) nobeti NO-OP yapilinca KIRMIZI yanmali mi?
    # Kaynak metni uzerinde iki gercek mutant uretilir ve AYRI bir modul ornegi olarak
    # yuklenir. Capa = nobetin KENDI tasiyici satirlari; capa bulunamazsa nobet zaten
    # kaldirilmis demektir -> KIRMIZI (fail-closed, ama capa dar: yorum/bosluk duzenlemesi
    # bu satirlari degistirmez).
    with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
        oz_kaynak = f.read()
    mutasyonlar = [
        ("MU1 tarihi kod geri konuldu (falsy kisa devre, dogrulamadan ONCE)",
         '        if "konfigur" not in u:\n            continue\n        if not u["konfigur"]:',
         '        if not u.get("konfigur"):\n            continue\n        if False:'),
        ("MU2 bos kayit RAPORLANMADAN atlaniyor (gurultu sokuldu)",
         '        if not u["konfigur"]:\n            uid_bos = u.get("id")',
         '        if not u["konfigur"]:\n            continue\n            uid_bos = u.get("id")'),
    ]
    mut_kacan = 0
    for ad, capa, yerine in mutasyonlar:
        if oz_kaynak.count(capa) != 1:
            kirmizi += 1
            mut_kacan += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK — nobet kaldirilmis ya da yeniden "
                       "yazilmis: " + ad)
            continue
        ns = {"__name__": "kbk_mutant", "__file__": os.path.abspath(__file__)}
        exec(compile(oz_kaynak.replace(capa, yerine), "<kbk-mutant>", "exec"), ns)
        s = kopya()
        s.insert(0, {"id": "bos-konfigur-vakasi", "kategori": "Skan Art", "baslik": "Bos",
                     "fiyat": "500 TL", "gorseller": [], "konfigur": {}})
        try:
            ns["turet"](s)
            ham.append("    ✅ " + ad + " -> mutant SESSIZ gecti = nobet YUK TASIYOR")
        except SystemExit:
            mut_kacan += 1
            kirmizi += 1
            ham.append("    ❌ OLU MUTASYON: " + ad + " -> mutant da reddetti, (E) bu satirlari "
                       "olcmuyor")
    ham.append("  (E-MUT) no-op mutasyonu: " + str(len(mutasyonlar)) + " denendi, " +
               str(mut_kacan) + " tanesi olcumsuz kaldi (0 olmali)")

    print("\n".join(ham))
    print("----------------------------------------------------------------------")
    print("SONUC: YESIL ✅ (kendini test)" if kirmizi == 0
          else "SONUC: KIRMIZI ❌ — " + str(kirmizi) + " blok kaldi")
    return 0 if kirmizi == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yaz", action="store_true", help="artefakti uret (tek bakim komutu)")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="kapinin kendi yanlis-pozitif + kirmizi-mutasyon olcumu")
    ap.add_argument("--urunler", default=URUNLER_VARSAYILAN)
    ap.add_argument("--dosya", default=ARTEFAKT_VARSAYILAN)
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    if a.yaz:
        return yaz(a.urunler, a.dosya)
    return kapi(a.urunler, a.dosya)


if __name__ == "__main__":
    sys.exit(main())
