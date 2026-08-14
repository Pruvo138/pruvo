#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARA MALIYET KAPISI — /ara'nin D1 sorgusu BIRLESIM SIRASI CEVRILIP tam taramaya dusuyor mu?

NEDEN VAR (olculmus canli olay, 31 Tem — MUSTERI 500 GORDU):
  Canli /ara ucu D1 CPU tavanini asip `D1_ERROR: D1 DB exceeded its CPU time limit and was
  reset` donduruyordu. Sirali prob: 30 istekten 5'i basarisiz (%16,7). Sinif bazinda:
  1-2 token'li sorgu %0, 3+ token'li sorgu %45,8, 10 token'li uzun sorgu %100.

  KOK NEDEN — SESSIZ BIR PLAN CEVRILMESI (indeks eksikligi DEGIL):
    araD1() sorgusu `urunler_fts f JOIN urunler u ON u.rid = f.rowid` uzerine her token
    icin bir `f.hs LIKE '%token%'` kosulu koyar. Token sayisi 1-2 iken SQLite planı
    FTS'ten surer:
        SCAN f VIRTUAL TABLE INDEX 0:L0L0     <- trigram indeksi calisiyor, UCUZ
    3 VE UZERI token'da maliyet tahmini degisir ve planlayici birlesim SIRASINI CEVIRIR:
        SEARCH u USING INDEX urunler_yayin (yayinda=?)
        SCAN f VIRTUAL TABLE INDEX 0:=L0L0L0  <- artik u DIS dongude
    Bu halde YAYINDAKI HER URUN icin ayri bir FTS aramasi yapilir -> tam tarama.
    Canli D1'de olculdu ('Volvo S60 far braketi'): rows_read=16.121, satir sorgusu
    6.810 ms + sayim sorgusu 6.465 ms = 13.275 ms TEK batch'te -> CPU tavani asilir.

  CEVRILMEYI MUMKUN KILAN SEY `urunler_yayin` INDEKSIDIR (atomik yayinla 31 Tem geldi:
  d1-sync.py YAYIN_INDEKS + araD1'e `u.yayinda = 1`). Indeks olmadan planlayicinin `u`'yu
  dis donguye alacak ucuz bir yolu YOKTU. Yani iki dogru degisiklik BIRLESINCE sessiz bir
  performans regresyonu dogurdu — ikisi de tek basina zararsizdi. Bu, kapinin ASIL dersi:
  regresyon SORGU METNINDE degil, PLANDA yasiyor.

  ONARIM: `JOIN` -> `CROSS JOIN`. SQLite'ta CROSS JOIN sonuc kumesini DEGISTIRMEZ, yalnizca
  planlayicinin birlesim sirasini yeniden duzenlemesini KAPATIR (f daima dis dongu). Ayni
  canli olcum onarimla: 13.275 ms -> 3,6 ms, rows_read 16.121 -> 9, DONEN SATIRLAR AYNI.

BU KAPI NE OLCER (iki eksen, ikisi de calistirilabilir):
  E1 SEMANTIK  — eski sekil, yeni sekil ve tools/arama.py'nin kanonik Python eslemesi
                 sorgu korpusunun TAMAMINDA birebir ayni id listesini VE ayni `toplam`i
                 donduruyor mu? Sapma = KIRMIZI. (Arama semantigi degismeyecek sarti
                 burada kanitlanir; parite-test.js canli uca bakar, bu kapi SQL SEKLINE
                 bakar — ikisi farkli eksendir.)
  E2 PLAN      — yeni sekilde plan `u`'yu dis donguye ALMIYOR mu (cevrilme yok) ve maliyet
                 butcenin altinda mi? Cevrilme = KIRMIZI, tek bir sorguda bile.

NICIN YEREL IKIZ: kapi agsiz ve deterministik olmali (CI'da kosabilsin, canli D1'in
oynakligina bagimli olmasin). Ikiz semayi ELLE TASIMAZ, gercek tanimi KOSAR:
  - tools/d1-sema.sql          dosyanin KENDISI executescript ile uygulanir,
  - d1-sync.py GOC_KOLON       sonradan eklenen kolonlarin ALTER'lari (canli --sema sirasi),
  - d1-sync.py YAYIN_INDEKS    urunler_yayin(_kat) — bilerek .sql'de DEGIL, o modulde.
Kolon listesi de PRAGMA table_info'dan turetilir; hs kolonu tools/arama.py haystack() ile,
yani D1'e yazan kodun TA KENDISI ile uretilir. Boylece "ikiz sessizce ayrisir" sinifi
KAPALIDIR: tanim degisirse ikiz DEGISIR, kaynak alinamazsa kapi OLCULEMEDI ile durur.
Arama SQL'i ve token tipleri de burada yeniden yazilmaz: tools/arama.py
`token_sozlesmesi_dogrula()` + `d1_site_sql_kur()` kosularak kanonik kaynaktan turetilir.

CAPA (kapinin KIRMIZI yanabilme sarti) DAVRANISTIR, yorum degil: her kosumda once
capa_dogrula() olayin SEKLINI (`JOIN`) kosturup plan cevrilmesinin HALA uretilebildigini
ve araD1'in SELECT listesinin bu semada cozuldugunu KANITLAR. Cevrilme tespiti indeks
ADINA degil plan SEKLINE baglidir (CEVRILME_DESEN), yani indeks yeniden adlandirilirsa
kapi kor kalmaz. Capa kaybolursa (cevrilme HIC dogmuyor / KART cozulmuyor) kapi SESSIZ
GECMEZ, "CAPA" diye KIRMIZI yanar.

CIKIS KODLARI:
  0 GECTI      — semantik birebir + hicbir sorguda plan cevrilmesi yok.
  1 SAPMA      — semantik ayrisma YA DA plan cevrilmesi (gercek bulgu).
  2 OLCULEMEDI — ikiz kurulamadi (urunler.json okunamadi, FTS5 trigram yok vb.).

KULLANIM:
    python3 tools/ara-maliyet-kapisi.py               # ~600 sorgu
    python3 tools/ara-maliyet-kapisi.py --adet 2000   # daha genis korpus
    python3 tools/ara-maliyet-kapisi.py --tut         # ikizi silme (tekrar kosum hizli)
"""
import argparse
import importlib.util
import json
import os
import random
import re
import sqlite3
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    import arama
except Exception as e:  # pragma: no cover
    print("OLCULEMEDI: tools/arama.py alinamadi: %s" % e)
    sys.exit(2)

# ── GERCEK SEMA TANIMI (ikizin TEK kaynagi; elle kopya YOK) ───────────────────
# Modul adi tire tasiyor -> duz `import` calismaz, importlib gerekir (d1-sync.py'nin
# konfigur-bundle-kapisi'ni almasiyla ayni desen).
SEMA_DOSYA = os.path.join(TOOLS, "d1-sema.sql")
_D1_YOL = os.path.join(TOOLS, "d1-sync.py")
try:
    _spec = importlib.util.spec_from_file_location("d1_sync_sema", _D1_YOL)
    _d1 = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_d1)
    YAYIN_INDEKS = list(_d1.YAYIN_INDEKS)   # SOZLESME SEMBOLU: adi degisirse burasi patlar
    GOC_KOLON = list(_d1.GOC_KOLON)
except Exception as e:  # pragma: no cover
    print("OLCULEMEDI: gercek sema tanimi alinamadi "
          "(tools/d1-sync.py YAYIN_INDEKS / GOC_KOLON): %s" % e)
    sys.exit(2)

# CEVRILME NEDIR (plan uzerinden, INDEKS ADINDAN BAGIMSIZ): `u` bir INDEKS uzerinden
# surulur -> u dis donguye gecmis, FTS ic dongude rowid ile aranıyor demektir; yani
# yayindaki her urun icin bir FTS aramasi = tam tarama.
#   SAGLIKLI:  SCAN f VIRTUAL TABLE INDEX 0:L0L0  /  SEARCH u USING INTEGER PRIMARY KEY
#   CEVRILMIS: SEARCH u USING INDEX <ad> (yayinda=?) / SCAN f VIRTUAL TABLE INDEX 0:=L0L0
# 🔴 NICIN AD DEGIL DESEN (olculdu 31 Tem): onceki hal duz metindi —
# "SEARCH u USING INDEX urunler_yayin". O metin `urunler_yayin_kat`i ONEK olarak
# YANLISLIKLA yakaliyordu (dogru sonuc, kaza eseri) ve indeks ADI degisse (ya da
# planlayici urunler_kat/urunler_seq'i secse) SESSIZCE kor kalirdi. Desen, cevrilmeyi
# ADA DEGIL SEKLE bagli olarak yakalar: hangi indeks olursa olsun.
CEVRILME_DESEN = re.compile(r"^(SEARCH|SCAN) u USING (COVERING )?INDEX ")


def cevrilmis_mi(plan, tokenlar):
    """Plan birlesim sirasini cevirmis mi? tokenlar BOSSA FTS birlesimi yoktur (kaynak
    duz `urunler u`), cevrilecek sira da yoktur -> False (yanlis-pozitif kapisi)."""
    if not tokenlar:
        return False
    return any(CEVRILME_DESEN.match(p) for p in plan)


# CAPA DAVRANIS TESTI: bu sorgular olayin 3+ token'li sinifindandir; olay SEKLI (`JOIN`)
# ile kosuldugunda plan cevrilmesi URETMELERI beklenir. Uretmiyorlarsa cevrilme artik
# YEREL IKIZDE HIC dogmuyor demektir ve kapinin yesili HICBIR SEY KANITLAMAZ.
OLAY_SORGULARI = [
    "Volvo S60 far braketi",
    "Grandland X havalandırma",
    "2016 passat b8 arka kapı iç açma kolu sağ taraf",
]


def yayin_indeks_adlari():
    """YAYIN_INDEKS'in KURDUGU indeks adlarini KOSARAK ogren (metin ayristirma YOK).

    Capa boylece ada elle bagli olmaz: tanimdaki ad degisirse bu liste de degisir.
    """
    t = sqlite3.connect(":memory:")
    t.execute("CREATE TABLE urunler (yayinda INTEGER, seq INTEGER, kategori TEXT)")
    t.executescript("\n".join(YAYIN_INDEKS))
    adlar = [r[0] for r in t.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='urunler'")]
    t.close()
    return adlar


def sema_uygula(c):
    """Gercek sema tanimini ikize KOSAR (elle kopya YOK) — canli `--sema` ile AYNI sira.

    1) tools/d1-sema.sql dosyasi aynen,
    2) d1-sync.GOC_KOLON  -> eksik kolonlarin ALTER'lari (taze ikizde no-op; canlida sira
       bu yuzden onemli: kolon YOKKEN yayin indeksi kurulamaz),
    3) d1-sync.YAYIN_INDEKS -> urunler_yayin / urunler_yayin_kat.
    Herhangi biri alinamaz/uygulanamazsa cagiran OLCULEMEDI ile durur (fail-closed):
    ikizi "yaklasik" kurup yesil yanmak, bu kapinin onlemek icin var oldugu seydir.
    """
    with open(SEMA_DOSYA, encoding="utf-8") as f:
        c.executescript(f.read())
    var = {r[1] for r in c.execute("PRAGMA table_info(urunler)")}
    for ad, tip in GOC_KOLON:
        if ad not in var:
            c.execute("ALTER TABLE urunler ADD COLUMN %s %s" % (ad, tip))
    c.executescript("\n".join(YAYIN_INDEKS))


# Tek sorgunun (satir + sayim) yerel ikizde harcayabilecegi azami VDBE adimi.
# KATALOG BOYUYLA OLCEKLENIR — sabit tavan katalog buyudukce SAHTE KIRMIZI verirdi:
# saglikli en kotu hal (tek 2 harfli token, or. "ic") trigram indeksini kullanamaz ve
# tam FTS taramasi yapar; maliyeti urun sayisiyla DOGRUSAL buyur (15.955 uründe VDBE~655k,
# yani urun basina ~41 adim). 250 = o dogrusal katsayinin ~6 kati.
# AYRISMA PAYI (kapinin isini yapabilmesi icin sart): cevrilmis plan AYNI katalogda
# 20-86 MILYON adim harciyor = butcenin 5-21 KATI. Yani saglikli tarafta %16'da geziyoruz,
# arizali tarafta butceyi 5 kattan fazla asiyoruz — arada 30 kata yakin bosluk var.
ADIM_BUTCESI_KATSAYI = 250
ADIM_BUTCESI_TABAN = 1_000_000
ADIM_BIRIMI = 1000


# Ikizin DEGER urettigi kolonlar (araD1'in okudugu alanlar + plan icin gereken anahtarlar).
# Geri kalan kolonlar semadan turetilir: NOT NULL + DEFAULT'suz olanlar notr doldurulur,
# DEFAULT'lular hic yazilmaz (semanin kendi varsayilani gecerli olur).
URETILEN_KOLON = ["rid", "id", "seq", "baslik", "kategori", "marka", "fiyat", "gorsel",
                  "parametrik", "hs", "aciklama", "yayinda"]


def ikiz_kur(yol, urunler):
    c = sqlite3.connect(yol)
    sema_uygula(c)
    tablo = {r[1]: {"tip": (r[2] or "").upper(), "notnull": r[3], "dflt": r[4], "pk": r[5]}
             for r in c.execute("PRAGMA table_info(urunler)")}
    eksik = [k for k in URETILEN_KOLON if k not in tablo]
    if eksik:
        raise sqlite3.OperationalError(
            "SEMA AYRISTI: ikizin deger urettigi kolon(lar) gercek semada YOK: %s" % eksik)
    # NOT NULL + DEFAULT'suz kolonlar (or. `hash`) doldurulmazsa INSERT patlar; PRAGMA'dan
    # turetildigi icin gercek semaya boyle bir kolon EKLENSE de ikiz kurulmaya devam eder.
    dolgu = [ad for ad, k in sorted(tablo.items())
             if ad not in URETILEN_KOLON and k["notnull"]
             and k["dflt"] is None and not k["pk"]]
    kolonlar = URETILEN_KOLON + dolgu
    dolgu_deger = [0 if tablo[ad]["tip"][:3] in ("INT", "REA", "NUM") else ""
                   for ad in dolgu]

    n = len(urunler)
    satirlar = []
    for i, u in enumerate(urunler):
        seq = n - i          # yeni urun urunler.json'un BASINDA -> en buyuk seq
        satirlar.append((seq, u.get("id") or "", seq, u.get("baslik") or "",
                         u.get("kategori") or "",
                         json.dumps(u.get("marka") or [], ensure_ascii=False),
                         u.get("fiyat") or "", (u.get("gorseller") or [None])[0],
                         1 if u.get("parametrik") else 0, arama.haystack(u),
                         (u.get("aciklama") or "")[:400], 1) + tuple(dolgu_deger))
    c.executemany(
        "INSERT INTO urunler (%s) VALUES (%s)" % (
            ", ".join(kolonlar), ", ".join("?" for _ in kolonlar)), satirlar)
    c.execute("INSERT INTO urunler_fts(urunler_fts) VALUES ('rebuild')")
    c.commit()
    return c


def ikiz_kapat(c, yol, dizin, tut):
    """Ikiz baglantisini kapatir; `--tut` yoksa uretilen gecici izi temizler."""
    if c is not None:
        c.close()
    if not tut:
        try:
            os.remove(yol)
            os.rmdir(dizin)
        except OSError:
            pass


def capa_dogrula(c, limit):
    """CAPA CANLI MI? — kapinin KIRMIZI yanabilmesinin SARTLARI, her kosumda kosarak.

    Guc sirasi: DAVRANIS > sozlesme sembolu > ham desen; yorum/serbest metin ASLA.
      (1) DAVRANIS (en guclu): olayin SEKLI (`JOIN`) hala plan cevrilmesi URETIYOR mu?
          Uretmiyorsa yerel ikizde olcecek bir risk kalmamistir; kapi yesil yanar ama o
          yesil HICBIR SEY kanitlamaz -> sessiz gecis yerine KIRMIZI.
      (2) araD1'in SELECT listesi (KART) bu semada COZULUYOR mu? Kolon dusmusse kapi
          olctugunu sandigi sorguyu hic kosamaz.
    Cevrilme ADA bagli olmadigindan (CEVRILME_DESEN) indeks yeniden adlandirilirsa kapi
    KOR KALMAZ, calismaya devam eder; capa ancak cevrilme HIC dogmadiginda olur.
    Doner: hata metinleri listesi. BOS = capa saglam. Dolu = KIRMIZI (sessiz gecis YOK).
    """
    hata = []
    try:
        c.execute("SELECT " + arama.D1_KART_ALANLARI + " FROM urunler u LIMIT 1").fetchall()
    except sqlite3.Error as e:
        hata.append("CAPA YOK: araD1 SELECT listesi (KART) bu semada cozulmuyor: %s" % e)

    uretti, surucu = 0, []
    for q in OLAY_SORGULARI:
        tk = arama.tokenlar(q)
        arama.token_sozlesmesi_dogrula(q, tk)
        (eski_s, eski_b), _ = arama.d1_site_sql_kur(tk, limit, "join")
        try:
            plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + eski_s, eski_b)]
        except sqlite3.Error as e:
            hata.append("CAPA YOK: olay sorgusu planlanamadi (%r): %s" % (q, e))
            continue
        if cevrilmis_mi(plan, tk):
            uretti += 1
            surucu += [p for p in plan if CEVRILME_DESEN.match(p)]
    if not uretti and not hata:
        hata.append(
            "CAPA OLDU: olayin SEKLI (`JOIN`) %d olay sorgusunun HICBIRINDE plan "
            "cevrilmesi uretmedi -> bu kapinin YESILI hicbir sey kanitlamaz. Yayin "
            "indeksleri (d1-sync.YAYIN_INDEKS: %s) dustu ya da planlayici davranisi "
            "degisti; kapinin varlik sebebi gozden gecirilmeli."
            % (len(OLAY_SORGULARI), yayin_indeks_adlari()))
    return hata, sorted(set(surucu))


def kos(c, sql, bag, adim_say=False):
    sayac = [0]
    if adim_say:
        def ilerle():
            sayac[0] += 1
            return 0
        c.set_progress_handler(ilerle, ADIM_BIRIMI)
    try:
        satir = c.execute(sql, bag).fetchall()
    finally:
        if adim_say:
            c.set_progress_handler(None, ADIM_BIRIMI)
    return satir, sayac[0] * ADIM_BIRIMI


def korpus(urunler, adet, tohum=20260731):
    """Sorgu korpusu — GERCEK katalog metninden turetilir (uydurma kelime degil).

    Token SAYISI bilerek 1..10 arasinda dagitilir: olay tam da token sayisina bagli
    (1-2 token saglikli, 3+ cevrilmis), yani kapinin korpusu o ekseni ORNEKLEMELI.
    """
    rast = random.Random(tohum)
    kelimeler = []
    for u in urunler:
        for w in arama.norm(u.get("baslik") or "").split():
            if len(w) >= 2:
                kelimeler.append(w)
    sorgular = [
        # Olayda CANLI 500 uretmis, isim isim tekrarlanabilir tetikleyiciler.
        "tekne", "Grandland X havalandırma", "Volvo S60 far braketi",
        "2016 passat b8 arka kapı iç açma kolu sağ taraf",
        "tekne güverte için paslanmaz olmayan halat tutucu braket",
        "göcek", "kapı kolu", "b8 x s6", "a4 x", "3d",
        "kapak kapak kapak kapak",
        "araba icin ozel uretim dayanikli plastik parca kapak",
        # Joker: LIKE'in % / _ karakterleri SITE'de DUZ HARF (araD1 instr ile bunu korur).
        "%kapak", "kapak_", "50%",
    ]
    if not kelimeler:
        return sorgular
    while len(sorgular) < adet:
        n = rast.choice([1, 1, 2, 2, 3, 3, 4, 5, 6, 8, 10])
        sorgular.append(" ".join(rast.choice(kelimeler) for _ in range(n)))
    return sorgular[:max(adet, len(sorgular))]


def kendini_test(c, limit):
    """KAPI GERCEKTEN KONUSUYOR MU? — onarim GERI ALINSA kirmizi yanar mi?

    Nobetci fikstur ilkesi: yesil yanan bir kapi, KIRMIZI yanabildigi kanitlanmadikca
    hicbir sey soylemez. Burada mutasyon gercek: `CROSS JOIN` -> `JOIN` (yani 31 Tem'de
    canlida 500 dondurmus SEKLIN TA KENDISI) ayni ikizde ayni sorgularla kosulur ve
    kapinin PLAN ekseninin onu YAKALAMASI beklenir.

    Bu sorgular BILEREK olaydaki 3+ token'li siniftan secilir — 1-2 token'li sorgu eski
    sekilde de saglikliydi, onunla yapilan bir "mutasyon testi" YESIL yanar ve kapinin
    kor oldugunu gizlerdi.
    """
    mutant_sorgular = OLAY_SORGULARI
    yakalanan, kacan = [], []
    for q in mutant_sorgular:
        tk = arama.tokenlar(q)
        arama.token_sozlesmesi_dogrula(q, tk)
        (eski_s, eski_b), _ = arama.d1_site_sql_kur(tk, limit, "join")
        plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + eski_s, eski_b)]
        if cevrilmis_mi(plan, tk):
            yakalanan.append((q, plan))
        else:
            kacan.append((q, plan))

    print("=== KENDINI TEST: mutasyon = `CROSS JOIN` -> `JOIN` (olayin sekli) ===")
    for q, plan in yakalanan:
        print("  YAKALANDI  %r" % q)
        for p in plan:
            print("      " + p)
    for q, plan in kacan:
        print("  🔴 KACTI    %r" % q)
        for p in plan:
            print("      " + p)
    if kacan:
        print("\n🔴 KAPI KOR: mutasyon %d/%d sorguda YAKALANMADI. Bu kapinin yesili"
              " HICBIR SEY KANITLAMAZ." % (len(kacan), len(mutant_sorgular)))
        return 1
    print("\n%d/%d mutant sorgu yakalandi -> kapinin PLAN ekseni CALISIYOR."
          % (len(yakalanan), len(mutant_sorgular)))

    # ── MUTASYON 2: CAPA KAYBI. Ikiz artik gercek semadan turetildigi icin, tanimdan
    # yayin indeksleri dusunce ikiz DE onlari kaybeder; cevrilme HIC dogmaz ve kapi
    # olcecek bir sey kalmadigi halde YESIL yanardi. Mutasyon AYNI ikizde GERCEK: adlar
    # YAYIN_INDEKS'i KOSARAK ogrenilir (elle liste yok), indeksler DROP edilir,
    # capa_dogrula() KIRMIZI yakmali; sonra ayni tanimdan geri kurulur — kalinti YOK.
    adlar = yayin_indeks_adlari()
    print("\n=== KENDINI TEST 2: mutasyon = gercek tanimdaki yayin indeksleri DUSURULDU"
          " (%s) ===" % ", ".join(adlar))
    onceki, _ = capa_dogrula(c, limit)
    for ad in adlar:
        c.execute("DROP INDEX " + ad)
    mutant_hata, _ = capa_dogrula(c, limit)
    c.executescript("\n".join(YAYIN_INDEKS))
    sonraki, _ = capa_dogrula(c, limit)
    for h in mutant_hata:
        print("  YAKALANDI  " + h)
    if onceki or sonraki:
        print("\n🔴 CAPA DOGRULAMASI TUTARSIZ: mutasyon YOKKEN de hata veriyor "
              "(once=%d, geri-kurulunca=%d) -> yanlis-pozitif riski." % (len(onceki),
                                                                         len(sonraki)))
        for h in onceki + sonraki:
            print("      " + h)
        return 1
    if not mutant_hata:
        print("\n🔴 CAPA KOR: capa dusurulunce capa_dogrula() KIRMIZI YAKMADI —"
              " kapi capasini kaybedince sessizce yesil yanar.")
        return 1
    print("capa mutasyonu %d hata ile yakalandi; indeksler geri kuruldu (kalinti yok)."
          % len(mutant_hata))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adet", type=int, default=600)
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--tut", action="store_true", help="ikiz veritabanini silme")
    ap.add_argument("--kendini-test", action="store_true",
                    help="yalniz mutasyon kabulu: kapi kirmizi yanabiliyor mu")
    a = ap.parse_args()

    try:
        with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
    except Exception as e:
        print("OLCULEMEDI: urunler.json okunamadi: %s" % e)
        return 2
    try:
        sqlite3.connect(":memory:").execute(
            "CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')")
    except Exception as e:
        print("OLCULEMEDI: yerel SQLite'ta FTS5 trigram yok: %s" % e)
        return 2

    dizin = tempfile.mkdtemp(prefix="ara-maliyet-")
    yol = os.path.join(dizin, "ikiz.db")
    t0 = time.time()
    try:
        c = ikiz_kur(yol, urunler)
    except Exception as e:
        # Fail-closed: ikiz GERCEK semadan kurulamadiysa olculecek bir sey yoktur.
        ikiz_kapat(None, yol, dizin, a.tut)
        print("OLCULEMEDI: ikiz gercek sema tanimindan kurulamadi "
              "(tools/d1-sema.sql + d1-sync.GOC_KOLON/YAYIN_INDEKS): %s" % e)
        return 2
    print("ikiz kuruldu: %d urun, %.1f sn (sema: tools/d1-sema.sql + d1-sync.GOC_KOLON"
          " + d1-sync.YAYIN_INDEKS)" % (len(urunler), time.time() - t0))

    butce = max(ADIM_BUTCESI_TABAN, len(urunler) * ADIM_BUTCESI_KATSAYI)

    # CAPA once dogrulanir: capa oldiyse asagidaki 600 sorguluk yesil ANLAMSIZDIR.
    try:
        capa_hata, surucu = capa_dogrula(c, a.limit)
    except (TypeError, ValueError, RuntimeError) as e:
        ikiz_kapat(c, yol, dizin, a.tut)
        print("OLCULEMEDI: tools/arama.py token/SQL sozlesmesi kullanilamadi: %s" % e)
        return 2
    if capa_hata:
        ikiz_kapat(c, yol, dizin, a.tut)
        print("\n🔴 CAPA — kapi olctugunu sandigi seyi olcemiyor (sessiz gecis YOK):")
        for h in capa_hata:
            print("  " + h)
        print("\n  NE YAPILMALI: sema tanimi (tools/d1-sema.sql / d1-sync.YAYIN_INDEKS)"
              " degistiyse bu kapinin CEVRILME_DESEN / KART / OLAY_SORGULARI capalari"
              " gozden gecirilmeli — kapi capasiz KOSMAZ.")
        return 1
    print("capa saglam: KART alanlari cozuluyor, olay sekli (`JOIN`) hala plan cevrilmesi"
          " uretiyor -> %s" % surucu)

    if a.kendini_test:
        kod = kendini_test(c, a.limit)
        ikiz_kapat(c, yol, dizin, a.tut)
        return kod

    sorgular = korpus(urunler, a.adet)
    semantik_sapma, plan_sapma = [], []
    en_kotu = (0, "")
    kanonik_hs = [(u.get("id") or "", arama.haystack(u)) for u in urunler]

    for q in sorgular:
        try:
            tk = arama.tokenlar(q)
            arama.token_sozlesmesi_dogrula(q, tk)
            (eski_s, eski_b), (eski_c, eski_cb) = arama.d1_site_sql_kur(
                tk, a.limit, "join")
            (yeni_s, yeni_b), (yeni_c, yeni_cb) = arama.d1_site_sql_kur(
                tk, a.limit, "cross")
        except (TypeError, ValueError, RuntimeError) as e:
            ikiz_kapat(c, yol, dizin, a.tut)
            print("OLCULEMEDI: tools/arama.py token/SQL sozlesmesi kullanilamadi "
                  "(q=%r): %s" % (q, e))
            return 2

        # ── E2 PLAN: yeni sekil `u`'yu dis donguye aliyor mu?
        plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + yeni_s, yeni_b)]
        if cevrilmis_mi(plan, tk):
            plan_sapma.append((q, tk, plan))
            continue   # cevrilmis planı KOSMA — kapiyi dakikalarca bekletir

        # Eski sekil cevrilmisse onu da KOSMAYIZ (olayin ta kendisi: 6-47 sn surerdi).
        eski_plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + eski_s, eski_b)]
        eski_cevrilmis = cevrilmis_mi(eski_plan, tk)

        yeni_satir, adim1 = kos(c, yeni_s, yeni_b, adim_say=True)
        yeni_sayim, adim2 = kos(c, yeni_c, yeni_cb, adim_say=True)
        adim = adim1 + adim2
        if adim > en_kotu[0]:
            en_kotu = (adim, q)
        if adim > butce:
            plan_sapma.append((q, tk, ["butce asildi: VDBE~%d > %d" % (adim, butce)]))
            continue

        if eski_cevrilmis:
            # Semantik ekseni yine olculur ama ESKI sekli kosmak olayin maliyetini
            # kapiya tasirdi. Bunun yerine eski sekil, planlayici cevrilmesinden
            # ETKILENMEYEN esdeger bir yolla dogrulanir: CROSS'suz ama FTS'siz duz tarama.
            # 🔴 KOSUL AYNEN KORUNUR (`u.hs LIKE ?` + AYNI baglar) — `instr()` KULLANILMAZ.
            # Sebep olculdu (31 Tem, CI kosumu 30654247130 ardili 30654284096): token'da
            # `%` / `_` varsa LIKE onlari JOKER, instr() DUZ HARF sayar; esdeger olmayan bu
            # yol korpusun joker sorgularinda ('%kapak' / 'kapak_' / '50%') eski=0 yeni=1997
            # /1985/1580 diye SAHTE semantik sapma uretti ve kapi TUM EKIBIN yayinini
            # durdurdu. Sapma YEREL makinede gorunmuyordu: hangi sorgunun ESKI planinin
            # cevrildigi SQLite SURUMUNE bagli, yani bu kol yalniz bazi ortamlarda giriliyor.
            # `f.hs` (content='urunler') ile `u.hs` AYNI kolondur -> LIKE'li duz tarama,
            # FTS birlesimli LIKE'in birebir esdegeridir.
            (duz, duz_b), (duz_c, duz_cb) = arama.d1_site_sql_kur(
                tk, a.limit, "duz")
            eski_satir, _ = kos(c, duz, duz_b)
            eski_sayim, _ = kos(c, duz_c, duz_cb)
        else:
            eski_satir, _ = kos(c, eski_s, eski_b)
            eski_sayim, _ = kos(c, eski_c, eski_cb)

        eski_id = [r[0] for r in eski_satir]
        yeni_id = [r[0] for r in yeni_satir]
        if eski_id != yeni_id or eski_sayim[0][0] != yeni_sayim[0][0]:
            semantik_sapma.append(("ESKI<>YENI", q, tk, eski_sayim[0][0],
                                   yeni_sayim[0][0], eski_id[:5], yeni_id[:5]))

        beklenen_tum = [urun_id for urun_id, hs in kanonik_hs if arama.esles(hs, tk)]
        beklenen_id = beklenen_tum[:a.limit]
        if yeni_id != beklenen_id or yeni_sayim[0][0] != len(beklenen_tum):
            semantik_sapma.append(("KANONIK<>SQL", q, tk, len(beklenen_tum),
                                   yeni_sayim[0][0], beklenen_id[:5], yeni_id[:5]))

    ikiz_kapat(c, yol, dizin, a.tut)
    if a.tut:
        print("ikiz TUTULDU: %s" % yol)

    print("\nsorgu=%d  semantik sapma=%d  plan sapmasi=%d" % (
        len(sorgular), len(semantik_sapma), len(plan_sapma)))
    print("en pahali sorgu: VDBE~%d  %r  (butce %d = %d urun x %d)" % (
        en_kotu[0], en_kotu[1], butce, len(urunler), ADIM_BUTCESI_KATSAYI))

    if semantik_sapma:
        print("\n🔴 SEMANTIK SAPMA — arama sonucu DEGISTI (onarim kabul EDILEMEZ):")
        for eksen, q, tk, es, ys, ei, yi in semantik_sapma[:20]:
            print("  eksen=%s q=%r token=%s  toplam referans=%s SQL=%s\n"
                  "    referans ilk: %s\n    SQL ilk: %s"
                  % (eksen, q, tk, es, ys, ei, yi))
    if plan_sapma:
        print("\n🔴 PLAN SAPMASI — birlesim sirasi cevrildi ya da butce asildi:")
        for q, tk, plan in plan_sapma[:20]:
            print("  q=%r token=%s" % (q, tk))
            for p in plan:
                print("      " + p)
        print("\n  NE YAPILMALI: worker/src/index.js araD1() icinde FTS birlesimi"
              " `CROSS JOIN` olarak KALMALI; `JOIN`'e donmus olabilir.")

    return 1 if (semantik_sapma or plan_sapma) else 0


if __name__ == "__main__":
    sys.exit(main())
