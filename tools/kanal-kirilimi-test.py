#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL BATARYASI — tools/kanal-kirilimi.py (fikstur D1; CANLI D1'E DOKUNMAZ).

Neyi olcer:
  T1  DORT kovanin DORDU DE dogru sayar (adet + ciro), kova adlari ciktida GORUNUR
  T2  🔴 `kanal` kolonu YOKKEN hukum OLCULEMEDI + SIFIR-DISI rc ("hepsi site" CIKARIMI YOK)
  T3  🔴 'bekliyor' / 'iptal' / 'havale-bekliyor' / 'basarisiz' / 'incele' CIROYA GIRMEZ
  T4  Tanimadigimiz kanal AYRI `OLCULEMEDI` satirinda gorunur + rc=2 (kovaya yutulmaz)
  T5  Ciro kurali ciktida BEYAN edilir (okuyan kaynak koda gitmek zorunda kalmasin)
  T6  Rapor kisisel veri kolonu SELECT ETMEZ (musteri_*/siparis_no sorguda GECMEZ)
  T7  🔴 MUTANT — hedef-kol atfiyla; KONTROL mutanti yesil kalmali

🔴 TEK KAYNAK KANITI: R1/R4 mutantlari shop/src/kanal-sinifi.js'i bozar ve BU PYTHON
raporunu kirmizi yakar; ayni mutantlar shop/test/kanal-gorunurluk.mjs'te de yaniyor.
Yani panel etiketi ile rapor kovasi GERCEKTEN ayni govdeden turuyor — ikisinden yalnizca
biri yansaydi "tek kaynak" iddiasi dekor olurdu.

Kosum:  python3 tools/kanal-kirilimi-test.py
"""
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "kanal-kirilimi.py")
SINIFLANDIRICI = os.path.join(KOK, "shop", "src", "kanal-sinifi.js")

SEMA_KANALLI = """
CREATE TABLE siparisler (
  id INTEGER PRIMARY KEY, siparis_no TEXT, tarih TEXT, durum TEXT,
  tutar_kurus INTEGER, kargo_kurus INTEGER, kdv_kurus INTEGER, atif TEXT,
  musteri_ad TEXT, musteri_tel TEXT, musteri_eposta TEXT, musteri_adres TEXT,
  kanal TEXT NOT NULL DEFAULT 'site', dis_no TEXT NOT NULL DEFAULT ''
);
"""
# 🔴 GOC KOSMAMIS HAL: kanal/dis_no kolonlari YOK (canlida bugun boyle olabilir).
SEMA_KANALSIZ = """
CREATE TABLE siparisler (
  id INTEGER PRIMARY KEY, siparis_no TEXT, tarih TEXT, durum TEXT,
  tutar_kurus INTEGER, kargo_kurus INTEGER, kdv_kurus INTEGER, atif TEXT,
  musteri_ad TEXT, musteri_tel TEXT, musteri_eposta TEXT, musteri_adres TEXT
);
"""

UCRETLI = '{"utm_source":"google","utm_medium":"cpc","utm_campaign":"yaz","ref":"REF:GS-MRN-9K2A"}'
ORGANIK = '{"utm_source":"bing","utm_medium":"organic","ref":"REF:OG-SEO-1B2C"}'
# 🔴 Yalniz kisi-kimligi tasiyan atif: KAYNAK soylemez -> siniflanamaz kovasina duser.
KIMLIK_ATFI = '{"ga_client_id":"GA1.1.9.8","fbp":"fb.1.1.x","fbc":"fb.1.1.y"}'

# (kanal, atif, durum, tutar, kargo) — beklenen kova yorumda.
SATIRLAR = [
    ("site", UCRETLI, "odendi", 10000, 2000),        # site-ucretli   ciro 120,00
    ("site", UCRETLI, "tamamlandi", 30000, 0),       # site-ucretli   ciro 300,00
    ("site", UCRETLI, "iptal", 99999, 99999),        # site-ucretli   CIRO DISI
    ("site", ORGANIK, "kargolandi", 5000, 1000),     # site-organik   ciro  60,00
    ("site", ORGANIK, "bekliyor", 88888, 0),         # site-organik   CIRO DISI
    ("site", "{}", "odendi", 4000, 500),             # atif-yok       ciro  45,00
    ("site", KIMLIK_ATFI, "odendi", 1000, 0),        # atif-yok       ciro  10,00
    ("site", "", "havale-bekliyor", 77777, 0),       # atif-yok       CIRO DISI
    ("whatsapp", "", "uretimde", 20000, 3000),       # whatsapp       ciro 230,00
    ("whatsapp", "", "basarisiz", 66666, 0),         # whatsapp       CIRO DISI
]
BEKLENEN = {
    "site-ucretli": {"adet": 3, "ciro_kurus": 42000, "ciro_disi_adet": 1},
    "site-organik": {"adet": 2, "ciro_kurus": 6000, "ciro_disi_adet": 1},
    "whatsapp": {"adet": 2, "ciro_kurus": 23000, "ciro_disi_adet": 1},
    "atif-yok": {"adet": 3, "ciro_kurus": 5500, "ciro_disi_adet": 1},
}

ARALIK = ("2026-08-01", "2026-09-01")


def fikstur(yol, sema, satirlar):
    conn = sqlite3.connect(yol)
    try:
        conn.executescript(sema)
        for i, (kanal, atif, durum, tutar, kargo) in enumerate(satirlar):
            if "kanal" in sema:
                conn.execute(
                    "INSERT INTO siparisler (siparis_no,tarih,durum,tutar_kurus,kargo_kurus,"
                    "kdv_kurus,atif,musteri_ad,musteri_tel,kanal) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    ("PR-%03d" % i, "2026-08-15T10:00:00Z", durum, tutar, kargo, 0, atif,
                     "GIZLI AD", "05550000000", kanal))
            else:
                conn.execute(
                    "INSERT INTO siparisler (siparis_no,tarih,durum,tutar_kurus,kargo_kurus,"
                    "kdv_kurus,atif,musteri_ad,musteri_tel) VALUES (?,?,?,?,?,?,?,?,?)",
                    ("PR-%03d" % i, "2026-08-15T10:00:00Z", durum, tutar, kargo, 0, atif,
                     "GIZLI AD", "05550000000"))
        conn.commit()
    finally:
        conn.close()


def arac_yukle(yol=None, siniflandirici=None):
    """Araci modul olarak yukle.

    Mutant kosumunda aracin KOPYASI gecici bir dizinden yuklenir; o kopyanin kendi
    `KOK`/`SINIFLANDIRICI` degerleri kendi konumundan turedigi icin YANLIS olur.
    Burada GERCEK yollara sabitlenir — mutasyon aracin MANTIGINI degistirir, YERINI
    degil. Sabitleme yapilmazsa mutant "dosya bulunamadi" ile coker ve kirmizi
    SEBEBI hedef kol OLMAZ ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
    """
    sys.path.insert(0, os.path.join(KOK, "tools"))
    hedef = yol or ARAC
    spec = importlib.util.spec_from_file_location("kanal_kirilimi_%d" % id(hedef), hedef)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.KOK = KOK
    m.SINIFLANDIRICI = siniflandirici or SINIFLANDIRICI
    return m


def kos_rapor(arac, db):
    return arac.olc(arac.sqlite_sorgucu(db), ARALIK[0], ARALIK[1])


# ------------------------------------------------------------------ IDDIALAR
def iddialar(arac_yolu=None, siniflandirici=None):
    """Doner: (gecti, hatalar). Her hata HEDEF KOL adiyla baslar."""
    hatalar = []
    gecti = [0]

    def iddia(kol, kosul, ek=""):
        if kosul:
            gecti[0] += 1
        else:
            hatalar.append("%s%s" % (kol, ("  → " + str(ek)[:220]) if ek else ""))

    arac = arac_yukle(arac_yolu, siniflandirici)
    dizin = tempfile.mkdtemp(prefix="kanal-kirilim-test-")
    try:
        db = os.path.join(dizin, "kanalli.db")
        fikstur(db, SEMA_KANALLI, SATIRLAR)
        r = kos_rapor(arac, db)

        # T1 — DORT kova, DORDU DE dogru
        iddia("T1/hukum", r["hukum"] == "OLCULDU", r.get("sebep"))
        iddia("T1/kova-sayisi", len(r.get("kovalar", [])) == 4, r.get("kovalar"))
        for kova, bek in BEKLENEN.items():
            v = (r.get("kirilim") or {}).get(kova)
            iddia("T1/%s-adet" % kova, v and v["adet"] == bek["adet"], v)
            # T3 ayni satirda olculur: ciro yalniz odendi-ve-sonrasi durumlardan gelir.
            iddia("T3/%s-ciro" % kova, v and v["ciro_kurus"] == bek["ciro_kurus"],
                  "beklenen %s bulunan %s" % (bek["ciro_kurus"], v and v["ciro_kurus"]))
            iddia("T3/%s-ciro-disi" % kova,
                  v and v["ciro_disi_adet"] == bek["ciro_disi_adet"], v)
        # 🔴 'atif-yok' kovasi ADIYLA GORUNUR olmali (sessizce organige katlanamaz).
        iddia("T1/atif-yok-ayri",
              (r["kirilim"]["atif-yok"]["adet"] > 0
               and r["kirilim"]["site-organik"]["adet"] == BEKLENEN["site-organik"]["adet"]),
              r.get("kirilim"))

        # T5 — ciro kurali ciktida BEYAN edilir
        satirlar = _yazdir(arac, r)
        iddia("T5/beyan", "CIRO KURALI" in satirlar and "odendi" in satirlar)
        iddia("T5/beyan-disarida-kalanlar", "CIROYA GIRMEZ" in satirlar)
        for kova in BEKLENEN:
            iddia("T5/kova-gorunur-%s" % kova, kova in satirlar)
        iddia("T5/olculemedi-satiri-daima", "OLCULEMEDI" in satirlar)
        # 🔒 Kisisel veri fikstürde DOLU; ciktida GECMEMELI.
        iddia("T6/ad-cikmiyor", "GIZLI AD" not in satirlar)
        iddia("T6/tel-cikmiyor", "05550000000" not in satirlar)
        for gizli in ("ga_client_id", "fbp", "fbc"):
            iddia("T6/gizli-%s" % gizli, gizli not in satirlar)

        # T6 — SELECT'te kisisel veri kolonu YOK (sorgu metni olculur)
        sqller = []
        r2 = arac.olc(_kaydeden(arac.sqlite_sorgucu(db), sqller),
                      ARALIK[0], ARALIK[1])
        iddia("T6/olcum-tekrarlanabilir", r2["hukum"] == r["hukum"])
        hepsi = " ".join(sqller)
        for kolon in ("musteri_ad", "musteri_tel", "musteri_eposta", "musteri_adres",
                      "musteri_notu", "siparis_no"):
            iddia("T6/select-%s" % kolon, kolon not in hepsi, hepsi[:200])

        # T2 — 🔴 kanal kolonu YOK -> OLCULEMEDI + rc=2
        db2 = os.path.join(dizin, "kanalsiz.db")
        fikstur(db2, SEMA_KANALSIZ, SATIRLAR)
        rk = kos_rapor(arac, db2)
        iddia("T2/hukum-olculemedi", rk["hukum"] == "OLCULEMEDI", rk)
        iddia("T2/kirilim-uretilmedi", "kirilim" not in rk, list(rk))
        iddia("T2/sebep-adiyla", "kanal" in rk.get("sebep", ""), rk.get("sebep"))
        iddia("T2/rc", _rc(arac, db2) == 2, _rc(arac, db2))

        # T4 — tanimadigimiz kanal AYRI satirda + rc=2
        db3 = os.path.join(dizin, "bilinmeyen.db")
        fikstur(db3, SEMA_KANALLI,
                SATIRLAR + [("instagram", UCRETLI, "odendi", 50000, 0)])
        rb = kos_rapor(arac, db3)
        iddia("T4/hukum-olculemedi", rb["hukum"] == "OLCULEMEDI", rb.get("sebep"))
        iddia("T4/olculemedi-adet", rb["olculemedi"]["adet"] == 1, rb.get("olculemedi"))
        iddia("T4/kanal-adiyla", "instagram" in rb["olculemedi"]["kanallar"],
              rb["olculemedi"])
        # Kovalara YUTULMADI: site-ucretli adedi degismedi.
        iddia("T4/kovaya-yutulmadi",
              rb["kirilim"]["site-ucretli"]["adet"] == BEKLENEN["site-ucretli"]["adet"],
              rb["kirilim"]["site-ucretli"])
        iddia("T4/rc", _rc(arac, db3) == 2)
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    return gecti[0], hatalar


def _kaydeden(sor, kova):
    def sar(sql):
        kova.append(sql)
        return sor(sql)
    return sar


def _yazdir(arac, rapor):
    import io
    import contextlib
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        arac.yazdir(rapor)
    return tampon.getvalue()


def _rc(arac, db):
    """Aracin GERCEK cikis kodu — 'hukum' alanindan cikarim DEGIL, main()'in dondurdugu."""
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return arac.main(["--sqlite", db, "--baslangic", ARALIK[0], "--bitis", ARALIK[1]])


# ------------------------------------------------------------------ MUTANTLAR
MUTANTLAR = [
    {"ad": "R1 'atif-yok' kovasi organige katlanir", "dosya": "js",
     "ara": "  if (!isaretVarMi(a)) { return KOVA_ATIF_YOK; }",
     "yaz": "  if (!isaretVarMi(a)) { return KOVA_SITE_ORGANIK; }",
     "kol": "T1/atif-yok-adet"},
    {"ad": "R2 'kanal' kolonu yokken sessizce 'site' sayilir", "dosya": "py",
     "ara": '        rapor["hukum"] = HUKUM_OLCULEMEDI\n'
            '        rapor["sebep"] = ("siparisler.kanal kolonu YOK',
     "yaz": '        rapor["hukum"] = HUKUM_OK\n'
            '        rapor["sebep"] = ("siparisler.kanal kolonu YOK',
     "kol": "T2/hukum-olculemedi"},
    {"ad": "R3 'iptal' ciroya girer", "dosya": "py",
     "ara": 'CIRO_DURUMLARI = ("odendi", "uretimde", "kargolandi", "tamamlandi")',
     "yaz": 'CIRO_DURUMLARI = ("odendi", "uretimde", "kargolandi", "tamamlandi", "iptal")',
     "kol": "T3/site-ucretli-ciro"},
    {"ad": "R4 bilinmeyen kanal sessizce bir kovaya yazilir", "dosya": "js",
     "ara": "  if (kanal !== KANAL_SITE && kanal !== KANAL_WHATSAPP) { return null; }",
     "yaz": "  if (kanal !== KANAL_SITE && kanal !== KANAL_WHATSAPP) { return KOVA_ATIF_YOK; }",
     "kol": "T4/hukum-olculemedi"},
    {"ad": "KONTROL (yalniz yorum — davranis AYNI)", "dosya": "py",
     "ara": "CIRO_DURUMLARI = (",
     "yaz": "# KONTROL MUTANTI — davranisa dokunmaz\nCIRO_DURUMLARI = (",
     "kol": None},
]


def mutant_kos(m):
    kaynak_yolu = SINIFLANDIRICI if m["dosya"] == "js" else ARAC
    with open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = f.read()
    if m["ara"] not in kaynak:
        # 🔴 Capa cokmesi SESSIZ GECILMEZ: mutant ULASMADIYSA olcum yapilmamistir.
        return {"hal": "CAPA_COKTU", "hatalar": [], "not": m["ara"][:70]}
    dizin = tempfile.mkdtemp(prefix="kanal-mutant-")
    try:
        hedef = os.path.join(dizin, os.path.basename(kaynak_yolu))
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(m["ara"], m["yaz"], 1))
        if m["dosya"] == "js":
            _, hatalar = iddialar(siniflandirici=hedef)
        else:
            _, hatalar = iddialar(arac_yolu=hedef)
        return {"hal": "KIRMIZI" if hatalar else "YESIL", "hatalar": hatalar}
    except Exception as e:                       # noqa: BLE001 (mutant coktu = kirmizi)
        return {"hal": "KIRMIZI", "hatalar": ["COKTU: %s" % e]}
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


def kos():
    gecti, hatalar = iddialar()
    print("TABAN  iddia=%d kirmizi=%d" % (gecti, len(hatalar)))
    for h in hatalar:
        print("  ✗ " + h)
    mutant_hatasi = 0
    toplam = 0
    for m in MUTANTLAR:
        toplam += 1
        r = mutant_kos(m)
        beklenen_hal = "KIRMIZI" if m["kol"] else "YESIL"
        hal_uygun = r["hal"] == beklenen_hal
        # 🔴 HEDEF-KOL ATFI: yalnizca "bir yerde kirmizi" yetmez.
        kolu_yakti = (any(h.startswith(m["kol"]) for h in r["hatalar"])
                      if m["kol"] else True)
        ok = hal_uygun and kolu_yakti
        if not ok:
            mutant_hatasi += 1
        print("%s %s  hal=%s%s%s" % (
            "✓" if ok else "✗", m["ad"], r["hal"],
            ("  kol='%s' %s" % (m["kol"], "YAKTI" if kolu_yakti else "YAKMADI"))
            if m["kol"] else "",
            ("  capa: " + r["not"]) if r.get("not") else ""))
        if not ok:
            for h in r["hatalar"][:3]:
                print("      | " + h)
    kirmizi = len(hatalar) + mutant_hatasi
    print("SONUC iddia=%d kirmizi=%d mutant=%d/%d"
          % (gecti, kirmizi, toplam - mutant_hatasi, toplam))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(kos())
