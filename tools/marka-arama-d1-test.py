#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — D1 `marka_arama` kolonu (marka SORGUSU eslesmesi) DOGRU doluyor mu?

  python3 tools/marka-arama-d1-test.py

SORUN (olculen SESSIZ hata, 5 Agu 2026 — musteri marka aramasinda ALAKASIZ urun goruyor):
canli arama UCTAN geliyor (index.html EDGE_KATALOG -> Worker `/ara`) ve uc `hs` uzerinde
ALT-DIZE aramasi yapiyor. Marka adiyla yapilan sorgu bu yuzden marka SAYFASINDAN cok daha
fazla urun donduruyor: `?q=MAN` = 3539 ("Mandali", "manuel"), `?q=Haval` = 581
("Havalandirma"), `43mm` -> "3M", "Land Rover" -> "Rover".
Site tarafi 8913db28 ile duzeltildi (fark 74 marka / 6.089 kalem -> 20 / 75) ama UC HALA
ESKI DAVRANISTA — yani Okan'in hukmu ("TUM markalarda sayfa ve arama urun adetlerinin ayni
olmasi") musteriye ULASMIYOR. Iki yuzey de kendi icinde tutarli gorundugu icin kimse
BILDIRMEZ = sessiz hata.

COZUM (bu testin olctugu sey): yuklem Worker'a KOPYALANMAZ (ikinci govde =
[[ikiz-tanim-sessiz-ayrisma]]); marka sorgusunun eslesecegi kanonik marka adlari SENKRON
ANINDA deponun TEK KAYNAKLARINDAN turetilip D1'e ONCEDEN yazilir. Uc yalnizca hazir degeri
okur (`EXISTS (SELECT 1 FROM json_each(marka_arama) WHERE value = ?)`).

🔴 BU TESTIN ASIL SAYISI (C bolumu): kolondan turetilen marka kumesi ile 8913db28 sonrasi
SITENIN urettigi kume 129/129 BIREBIR. Iddia EZBERDEN degil, gercek katalogdan olculur ve
REFERANS BASKA BIR GOVDEDEN gelir (tools/marka-invaryant-kapisi.py :: olc) — ayni dosyadan
turetilseydi totoloji olurdu.

🔴 S BOLUMU — IKI KOLON ARASINDAKI SOZLESME: `marka_arama ⊇ marka_kanon`. Ayri kolon olmasi
MIMAR KARARIDIR (marka_kanon cipi besler ve UYELIK tanimini tasimalidir; baslik uyumu ona
eklenseydi cip sayfadan fazla sayar ve marka-invaryant-kapisi.py FILTRE ekseni bozulurdu).
Iliski VARSAYILMAZ, OLCULUR.

Bu test CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek tools/d1-sema.sql'i yerel bir
sqlite3'e yukler, gercek d1-sync fonksiyonlarini (marka_arama_haritasi, marka_arama_plan)
ve gercek urunler.json'u kullanir.

MUTASYON KANITI REPODA KOSULABILIR: tools/marka-arama-mutasyon.py
([[mutasyon-kaniti-yeniden-uretilebilir]] — anlatilan batarya kanit DEGILDIR).
"""
import importlib.util
import json
import os
import re
import sqlite3
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
SEMA = os.path.join(TOOLS, "d1-sema.sql")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

gecen = [0]
kalan = [0]
ATLANAN = []


def dogrula(ad, kosul, detay=""):
    """🔴 `detay` DAIMA metne cevrilir: liste/None verilen bir cagri, iddia KALDIGINDA
    TypeError ile COKERDI — mutasyon surucusu bunu 'kirmizi ama olculen iddia yok' diye
    COKME sayar ve OLDURUCU mutant sessizce hayatta kalirdi (M7'de fiilen olculdu)."""
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — %s" % (detay,) if detay else ""))


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def trigram_var_mi():
    """CI ubuntu'nun stok sqlite3'unde fts5-trigram YOK (marka-kanon-d1-test.py ayni olcum).
    Bu testin iddialari FTS'e IHTIYAC DUYMAZ; kabiliyet OLCULUR, muafiyet yazilmaz."""
    if os.environ.get("PRUVO_FTS_YOK") == "1":
        return False
    try:
        c = sqlite3.connect(":memory:")
        c.executescript("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram');")
        c.close()
        return True
    except sqlite3.Error:
        return False


FTS = trigram_var_mi()


def _sema_metni():
    """d1-sema.sql; trigram yoksa FTS5 sanal tablosu + ona bagli tetikler CIKARILIR."""
    ham = open(SEMA, encoding="utf-8").read()
    if FTS:
        return ham
    cikti, atla, tetik = [], False, False
    for satir in ham.splitlines(True):
        k = satir.strip().lower()
        if not atla:
            if k.startswith("create trigger urunler_a"):
                atla, tetik = True, True
            elif (k.startswith("create virtual table")
                  or k.startswith("drop trigger if exists urunler_a")):
                atla, tetik = True, False
        if atla:
            if (tetik and k == "end;") or (not tetik and satir.rstrip().endswith(";")):
                atla = False
            continue
        cikti.append(satir)
    return "".join(cikti)


def yeni_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(_sema_metni())
    return conn


def json1_var_mi(conn):
    try:
        conn.execute("SELECT 1 FROM json_each('[\"a\"]')").fetchone()
        return True
    except sqlite3.Error:
        return False


def sema_kolonlari(metin, tablo):
    m = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?%s\s*\((.*?)\n\);" % tablo, metin, re.S)
    if not m:
        return {}
    out = {}
    for satir in m.group(1).splitlines():
        s = satir.strip()
        if not s or s.startswith("--"):
            continue
        p = s.rstrip(",").split()
        if len(p) >= 2 and p[0].isidentifier():
            out[p[0]] = p[1]
    return out


# ── kaynaklar ───────────────────────────────────────────────────────────────────
d1 = yukle_modul("d1_sync_ma", "d1-sync.py")
kapi = yukle_modul("marka_invaryant_kapisi_ma", "marka-invaryant-kapisi.py")
import arama                                                          # noqa: E402
import marka_model_build as mmb                                       # noqa: E402

URUNLER = json.load(open(os.path.join(KOK, "urunler.json"), encoding="utf-8"))
INDEX = open(os.path.join(KOK, "index.html"), encoding="utf-8").read()

# ── SEMANTIK FIKSTUR — KATALOGDAN BAGIMSIZ (veri partisi bayatlatamaz) ──────────
# 🔴 NEDEN SENTETIK: bu iddialar JETONLAMA SEMANTIGI hakkindadir. Gercek urun id'sine
# civilenseydi MaCiT'in bir sonraki partisi capayi eritir ve iddia sessizce kaybolurdu
# (marka-invaryant-kapisi.py'de AYNEN yasandi). Kullanilan markalarin hepsi index.html
# TANINMIS_MARKALAR'dadir, yani cip evreninden BAGIMSIZ tanINIR.
# (id, marka[], baslik, kolonda OLMALI, kolonda OLMAMALI, ne kanitlar)
FIKSTURLER = [
    ("fx-land-rover", [], "Land Rover Defender Kapi Kolu Kapagi",
     ["Land Rover"], ["Rover"],
     "UZUN-ONCE: bigram tutunca tekil 'Rover' URETILMEZ (farkli marque)"),
    ("fx-rover", [], "Rover 75 Torpido Klipsi", ["Rover"], [],
     "KONTROL: 'Land' oneki YOKKEN tekil Rover DOGAR (kural 'Rover'i hep ezmek degil)"),
    ("fx-yamaha-mercury", [], "Sierra 18-8076 Yamaha Mercury Ortak Tip Benzin Fisi",
     ["Yamaha", "Mercury"], [],
     "ONEK KATLAMASI METINDE YOK: bitisik ikinci marka jetonu YUTULMAZ"),
    ("fx-alfa", [], "Alfa Romeo 156 Vites Topuzu", ["Alfa Romeo"], [],
     "COK KELIMELI marka BUTUN kalir"),
    ("fx-haval", [], "Suzuki Samurai Kalorifer Havalandirma Dugmesi", ["Suzuki"], ["Haval"],
     "MORFOLOJIK GURULTU: 'Havalandirma' TAM KELIME 'Haval' DEGILDIR"),
    ("fx-man", [], "Nissan Altima Torpido Gozu Mandali", ["Nissan"], ["MAN"],
     "MORFOLOJIK GURULTU: 'Mandali' TAM KELIME 'MAN' DEGILDIR"),
    ("fx-uyelik", ["Volvo Penta"], "Hava Filtresi 18-7908", ["Volvo"], [],
     "UYELIK KOLU: baslikta marka YOKKEN katlanmis uyelik kolona GIRER"),
    ("fx-bos", [], "Torpido Klipsi", [], ["Volvo", "Rover", "MAN"],
     "ESLESMESI OLMAYAN urun haritaya HIC girmez (hedef '[]' = D1 varsayilani)"),
]

# ── GURULTU CAPASI — GERCEK KATALOG (serbest metne geri donusu yakar) ───────────
# marka-invaryant-kapisi.py GURULTU_CAPALARI ile AYNI urunler: bugun uctaki serbest metin
# `?q=<marka>` sonucunda CIKIYORLAR ve HICBIRI o markayla ilgili DEGIL. Kolonda OLMAMALI.
GURULTU_CAPALARI = [
    ("suzuki-samurai-kalorifer-havalandirma-dugmesi", "Haval",
     "morfolojik (Havalandirma -> 'haval')"),
    ("nissan-altima-torpido-gozu-mandali", "MAN", "morfolojik (Mandali -> 'man')"),
    ("suzuki-dl650-v-strom-43mm-kece-montaj-aleti", "3M", "alt-dize (43mm -> '3m')"),
    ("land-rover-defender-orta-konsol-govdesi-1997-2000", "Rover",
     "farkli marque ayni ad (Land Rover -> 'Rover'; UZUN-ONCE kurali keser)"),
]


# ══ A) IKIZ TANIM — kolon dogru SINIFTA mi ═══════════════════════════════════════
print("\n[A] IKIZ TANIM — kolon nerede tanimli, hangi senkron sinifinda")
sema = sema_kolonlari(open(SEMA, encoding="utf-8").read(), "urunler")
goc = dict(d1.GOC_KOLON)
kt = sema_kolonlari(d1._KT_SEMA, "urunler")
ins = re.search(r"INSERT INTO urunler \(([^)]*)\)",
                d1.satir_sql({"id": "a", "marka": []}, 1, "hs", "h")).group(1).split(",")
dogrula("A1 `marka_arama` d1-sema.sql CREATE TABLE'da (temiz DB ayni semayi alir)",
        sema.get("marka_arama") == "TEXT", sema.get("marka_arama"))
dogrula("A2 `marka_arama` GOC_KOLON'da (canli tablo ALTER ile alir)",
        "marka_arama" in goc, sorted(goc))
dogrula("A3 GOC_KOLON DEFAULT'u '[]' ('' DEGIL — okuma ucu JSON.parse'i kosulsuz uygular)",
        "'[]'" in goc.get("marka_arama", ""), goc.get("marka_arama"))
dogrula("A4 `marka_arama` _KT_SEMA'da (offline fikstur canli semadan AYRISMAZ)",
        kt.get("marka_arama") == "TEXT", kt.get("marka_arama"))
# 🔴 SINIF: hash'e KARISMAZ -> icerik upsert'inde OLMAMALI. Deger urunun `marka` dizisine
# oldugu kadar BASLIGINA ve index.html KURATORLUGUNE de baglidir; icerik upsert'ine
# baglansaydi yeni bir marka TANINMIS listeye eklendiginde hicbir hash degismez ve kolon
# SONSUZA DEK bayat kalirdi.
dogrula("A5 `marka_arama` satir_sql INSERT listesinde DEGIL (hedefli UPDATE sinifi)",
        "marka_arama" not in [k.strip() for k in ins], ins)
dogrula("A6 `marka_arama` KOLONLAR'da DEGIL (ON CONFLICT yolu ona DOKUNMAZ)",
        "marka_arama" not in d1.KOLONLAR)

# ══ B) TURETIM — tek kaynak + SENTETIK SEMANTIK FIKSTUR ══════════════════════════
print("\n[B] TURETIM — tek kaynak + katalogdan BAGIMSIZ jetonlama fiksturleri")
fikstur_urun = [{"id": fid, "marka": list(mk), "baslik": bs, "kategori": "Otomobil",
                 "fiyat": "100 TL", "aciklama": ""}
                for fid, mk, bs, _i, _ie, _k in FIKSTURLER]
fx_harita, fx_sebep = d1.marka_arama_haritasi(fikstur_urun)
dogrula("B0 fikstur turetimi BASARILI (sebep None)", fx_sebep is None, str(fx_sebep))
for fid, _mk, bs, icermeli, icermemeli, kanit in FIKSTURLER:
    kol = json.loads(fx_harita.get(fid, "[]"))
    eksik = [m for m in icermeli if m not in kol]
    sizan = [m for m in icermemeli if m in kol]
    dogrula("B1 FIKSTUR %s | %s -> %s (eksik: %s · sizan: %s)"
            % (kanit, bs[:44], kol, eksik or "-", sizan or "-"),
            not eksik and not sizan)

harita, sebep = d1.marka_arama_haritasi(URUNLER)
dogrula("B2 GERCEK KATALOG turetimi BASARILI (fail-closed dalina DUSMEDI)",
        sebep is None, str(sebep))
degerler = set()
for v in harita.values():
    degerler.update(json.loads(v))
dogrula("B3 harita DOLU: %d urun, %d ayri kanonik marka degeri"
        % (len(harita), len(degerler)), len(harita) > 1000 and len(degerler) > 100,
        "%d / %d" % (len(harita), len(degerler)))

# GURULTU CAPASI (gercek katalog): capa TAM BIR KEZ gecmeli, kolonda OLMAMALI.
kimlik_sayaci = {}
for p in URUNLER:
    if p.get("id"):
        kimlik_sayaci[p["id"]] = kimlik_sayaci.get(p["id"], 0) + 1
for pid, marka, sinif in GURULTU_CAPALARI:
    if kimlik_sayaci.get(pid, 0) != 1:
        dogrula("B4 GURULTU CAPASI %s (%s): katalogda TAM BIR KEZ gecmeli (bulunan: %d)"
                % (pid, sinif, kimlik_sayaci.get(pid, 0)), False)
        continue
    kol = json.loads(harita.get(pid, "[]"))
    dogrula("B4 GURULTU CAPASI %s -> marka_arama '%s' ICERMEZ (%s)" % (pid, marka, sinif),
            marka not in kol, str(kol))

# ══ C) SITE PARITESI — kolon SITENIN urettigi kumeyi mi tasiyor ══════════════════
# 🔴 REFERANS BASKA BIR GOVDEDEN: marka-invaryant-kapisi.olc() kumeleri kendi kurar.
# Ayni dosyadan turetilseydi totoloji olurdu; bu ayrim sayesinde marka_arama_haritasi'na
# uygulanan bir mutant (baslik kolunu at, yuklemi serbest metne cevir) KIRMIZI yanar.
print("\n[C] SITE PARITESI — kolondan turetilen marka kumesi = SITENIN kumesi mi")
try:
    veri, kumeler, serbeste_dusen, _uyelik, _bs, _kanon = kapi.olc(mmb, arama, URUNLER, INDEX)
except SystemExit as e:                                               # noqa: BLE001
    veri, kumeler, serbeste_dusen = {}, {}, []
    ATLANAN.append("site referansi (marka-invaryant-kapisi.olc) kosulamadi: SystemExit %s"
                   % (e.code,))

kolon_kume = {}
for uid, v in harita.items():
    for m in json.loads(v):
        kolon_kume.setdefault(m, set()).add(uid)

if kumeler:
    sapan = []
    for marka, (_sayfa, _filtre, srch) in kumeler.items():
        kol = kolon_kume.get(marka, set())
        if kol != srch:
            sapan.append((marka, len(srch - kol), len(kol - srch)))
    dogrula("C1 🔴 kolon kumesi = SITENIN `?q=<marka>` kumesi, %d/%d markada BIREBIR "
            "(sapan: %s)" % (len(kumeler) - len(sapan), len(kumeler), sapan[:6]), not sapan)
    dogrula("C2 her kanonik marka adi MARKA SORGUSU olarak taniniyor (serbeste dusen: %d %s)"
            % (len(serbeste_dusen), serbeste_dusen[:4]), not serbeste_dusen)
    ornek = sorted(((len(v), m) for m, v in kolon_kume.items() if m in kumeler),
                   reverse=True)[:3]
    dogrula("C3 ornek — en buyuk uc marka kumesi kolonda: %s"
            % ", ".join("%s=%d" % (m, n) for n, m in ornek), bool(ornek))
else:
    ATLANAN.append("C bolumu (site paritesi) OLCULEMEDI — referans govde kosmadi")

# ══ S) SOZLESME — marka_arama ⊇ marka_kanon ══════════════════════════════════════
print("\n[S] SOZLESME — marka_arama ⊇ marka_kanon (ayri kolon olmasinin bedeli)")
kanon_harita, kanon_sebep = d1.marka_kanon_haritasi(URUNLER)
dogrula("S0 marka_kanon turetimi BASARILI", kanon_sebep is None, str(kanon_sebep))
ihlal = []
for uid, v in kanon_harita.items():
    kol = set(json.loads(harita.get(uid, "[]")))
    for m in json.loads(v):
        if m not in kol:
            ihlal.append((uid, m))
dogrula("S1 🔴 UST KUME IHLALI = %d (marka_kanon'daki her kanonik ad marka_arama'da da VAR)"
        % len(ihlal), not ihlal, str(ihlal[:5]))
dogrula("S2 marka_arama marka_kanon'dan GENIS (baslik kolu FIILEN olculuyor): "
        "marka_arama %d satir · marka_kanon %d satir" % (len(harita), len(kanon_harita)),
        len(harita) > len(kanon_harita),
        "%d vs %d" % (len(harita), len(kanon_harita)))

# ══ K) KAYIPSIZLIK — uca 'tek basina mi, birlesim mi' hukmu ══════════════════════
print("\n[K] KAYIPSIZLIK — ham `marka` ile karsilastirma (uca verilecek hukum)")
ham_jeton, kayip_jeton, kayip_kalem = set(), set(), 0
marka_adi_kayip = []
ham_esitlik_fazla = []
for p in URUNLER:
    pid = p.get("id")
    if not pid:
        continue
    kol = set(json.loads(harita.get(pid, "[]")))
    for t in (p.get("marka") or []):
        t = (t or "").strip()
        if not t:
            continue
        ham_jeton.add(t)
        if t not in kol:
            kayip_jeton.add(t)
            kayip_kalem += 1
            # 🔴 ASIL EKSEN: kaybolan jeton bir KANONIK MARKA ADI mi? Degilse (model kodu,
            # donanim jetonu) uc onu zaten SERBEST METIN kolunda bulur -> kayip DEGIL.
            if t in kolon_kume or (kumeler and t in kumeler):
                marka_adi_kayip.append((pid, t))
    # HAM ESITLIK ⊆ KOLON: uc `marka_arama ∪ ham marka` BIRLESIMI kullansaydi ne EKLENIRDI?
    for t in (p.get("marka") or []):
        if kumeler and t in kumeler and t not in kol:
            ham_esitlik_fazla.append((pid, t))
print("  ham jeton %d · kolonda gecmeyen jeton %d / kalem %d"
      % (len(ham_jeton), len(kayip_jeton), kayip_kalem))
dogrula("K1 🔴 kolonda gecmeyen ham jetonlarin HICBIRI kanonik marka adi DEGIL "
        "(hepsi model/donanim jetonu -> uc onlari SERBEST METIN kolunda bulur): ihlal %d"
        % len(marka_adi_kayip), not marka_adi_kayip, str(marka_adi_kayip[:5]))
dogrula("K2 🔴 HAM ESITLIK ⊆ KOLON: `marka_arama ∪ ham marka` BIRLESIMI %d kalem EKLER "
        "-> uc BIRLESIME IHTIYAC DUYMAZ, kolon TEK BASINA yeter"
        % len(ham_esitlik_fazla), not ham_esitlik_fazla, str(ham_esitlik_fazla[:5]))
ters = 0
if kumeler:
    for m, uidler in kolon_kume.items():
        if m in kumeler:
            ters += len(uidler - kumeler[m][2])
    dogrula("K3 TERS YON: kolonda VAR ama sitenin kumesinde YOK = %d (0 olmali)" % ters,
            ters == 0)
else:
    ATLANAN.append("K3 (ters yon) OLCULEMEDI — site referansi kosmadi")

# ══ D) SQLITE IKIZI + IDEMPOTENS + OLCEK ═════════════════════════════════════════
print("\n[D] SQLITE IKIZI — retrofit · idempotens · olcek")
conn = yeni_db()
conn.row_factory = sqlite3.Row
for i, p in enumerate(URUNLER):
    if not p.get("id"):
        continue
    conn.execute(
        "INSERT INTO urunler (rid,id,hash,seq,baslik,kategori,marka,hs) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (i + 1, p["id"], arama.urun_hash(p), len(URUNLER) - i, p.get("baslik") or "",
         p.get("kategori") or "", json.dumps(p.get("marka") or [], ensure_ascii=False),
         arama.haystack(p)))
conn.commit()
toplam = conn.execute("SELECT COUNT(*) c FROM urunler").fetchone()["c"]
bos = conn.execute("SELECT COUNT(*) c FROM urunler WHERE marka_arama='[]'").fetchone()["c"]
dogrula("D1 retrofit ONCESI: TUM %d satir D1 varsayilaninda ('[]')" % toplam, bos == toplam)

mevcut = {r["id"]: r["marka_arama"] for r in
          conn.execute("SELECT id, marka_arama FROM urunler")}
plan = d1.marka_arama_plan(URUNLER, harita, mevcut)
dogrula("D2 plan TAM %d UPDATE uretir (eslesmesi olmayan urune DOKUNMAZ — olcek kapisi)"
        % len(harita), len(plan) == len(harita),
        "plan=%d harita=%d" % (len(plan), len(harita)))
for sql in plan:
    conn.executescript(sql)
conn.commit()
doldu = conn.execute("SELECT COUNT(*) c FROM urunler WHERE marka_arama<>'[]'").fetchone()["c"]
ayri = len(degerler)
dogrula("D3 kolon DOLDU: %d satir · %d ayri deger (dokunulmayan %d satir '[]' kaldi)"
        % (doldu, ayri, toplam - doldu), doldu == len(harita))

# UCUN SORGU BICIMI — kolon boyle okunacak.
json1 = json1_var_mi(conn)
if json1:
    ornek_marka = sorted(kolon_kume, key=lambda m: -len(kolon_kume[m]))[0]
    n = conn.execute(
        "SELECT COUNT(*) c FROM urunler WHERE EXISTS "
        "(SELECT 1 FROM json_each(urunler.marka_arama) WHERE value = ?)",
        (ornek_marka,)).fetchone()["c"]
    dogrula("D4 UCUN SORGUSU (json_each) '%s' icin %d satir dondurur = turetilen kume"
            % (ornek_marka, n), n == len(kolon_kume[ornek_marka]),
            "%d vs %d" % (n, len(kolon_kume[ornek_marka])))
else:
    ATLANAN.append("sqlite JSON1 yok -> ucun SORGU BICIMI (json_each) olculmedi; kolonun "
                   "ICERIGI Python tarafinda dogrulandi")

mevcut2 = {r["id"]: r["marka_arama"] for r in
           conn.execute("SELECT id, marka_arama FROM urunler")}
dogrula("D5 idempotent: D1 zaten dogruysa 0 UPDATE (her push'ta thrash YOK)",
        d1.marka_arama_plan(URUNLER, harita, mevcut2) == [])
eslesmesiz = [p for p in URUNLER if p.get("id") and p["id"] not in harita]
dogrula("D6 eslesmesi olmayan %d urune HIC dokunulmaz (hedef '[]' = D1 varsayilani)"
        % len(eslesmesiz), d1.marka_arama_plan(eslesmesiz, harita, {}) == [])
# 🔴 VARSAYILAN EKSENI — AYIRT EDICI FIKSTUR (D1'deki GERCEK hal '[]'dir): varsayilan='[]'
# ile 0 UPDATE; sema_plan'in eski sabiti '' ile hedef '' != '[]' -> her satira bos UPDATE.
# Fikstur '[]' TASIMASAYDI iki cagri da 0 doner ve eksen SESSIZCE olculmezdi
# ([[fikstur-degeri-mutasyon-koru]]).
d1_hali = {p["id"]: "[]" for p in eslesmesiz[:50]}
dogrula("D7 sema_plan varsayilani '[]' ile cagriliyor (yoksa eslesmesiz urunlerin HEPSINE "
        "bos UPDATE dogardi)",
        d1.sema_plan("marka_arama", eslesmesiz[:50], {}, d1_hali, None, varsayilan="[]") == []
        and len(d1.sema_plan("marka_arama", eslesmesiz[:50], {}, d1_hali, None)) == 50,
        "%d / %d"
        % (len(d1.sema_plan("marka_arama", eslesmesiz[:50], {}, d1_hali, None,
                            varsayilan="[]")),
           len(d1.sema_plan("marka_arama", eslesmesiz[:50], {}, d1_hali, None))))

# ══ E) FAIL-CLOSED — "BOSALT" DEGIL "DOKUNMA" ════════════════════════════════════
print("\n[E] FAIL-CLOSED — tek kaynak okunamazsa kolon BOSALTILMAZ")
_gercek_kok = d1.KOK
try:
    d1.KOK = os.path.join(TOOLS, "fikstur", "__yok__")
    bos_harita, bos_sebep = d1.marka_arama_haritasi(URUNLER)
    dogrula("E1 index.html okunamayinca SEBEP doner (sessiz bos harita YOK)",
            bos_sebep is not None and bos_harita == {}, str(bos_sebep))
finally:
    d1.KOK = _gercek_kok
kaynak = open(os.path.join(TOOLS, "d1-sync.py"), encoding="utf-8").read()
dogrula("E2 sebep DOLUYKEN main plani KOSMAZ — kaynak metinde kosul VAR",
        "not marka_arama_sebep" in kaynak)
zarar = d1.marka_arama_plan(URUNLER, {}, mevcut2)
dogrula("E3 (kontrfaktuel) bos harita ile kosulsaydi %d satir '[]' YAPILIRDI — bu yuzden "
        "atlanir" % len(zarar), len(zarar) == len(harita))
# BELLEK NOBETI: ortak kaynak bellegi fail-closed dalini SESSIZCE gecirmemeli.
dogrula("E4 ortak kaynak bellegi KOK'u anahtara alir (bellek fail-closed dalini yutmaz)",
        "anahtar = (id(urunler), KOK)" in kaynak)

# ══ F) SEMA SIRASI — kolonu SELECT eden kod ONCE push'lanabilir mi ═══════════════
print("\n[F] SEMA SIRASI — 'no such column' ile herkesin push'unu kirma riski")
dogrula("F1 d1_mevcut SELECT'i marka_arama'yi KOSULLU ekler (kolon yoksa istemez)",
        '", marka_arama" if marka_arama_kolonu else ""' in kaynak)
dogrula("F2 kolon varligi PRAGMA'dan okunur (tablo_kolonlari)",
        '"marka_arama" in tablo_kolonlari' in kaynak)
dogrula("F3 marka_arama ZORUNLU_KOLONLAR'da DEGIL (yoklugu senkronu DUSURMEZ)",
        "marka_arama" not in d1.ZORUNLU_KOLONLAR, d1.ZORUNLU_KOLONLAR)
dogrula("F4 geri-okuma da KOSULLU (kolon yokken SELECT'e girmez)",
        '(["marka_arama"] if marka_arama_kolonu else [])' in kaynak)
# FIILI SINAMA: kolonu OLMAYAN bir tabloda SELECT ifadesi 'no such column' vermemeli.
eski_db = sqlite3.connect(":memory:")
eski_db.executescript("CREATE TABLE urunler (id TEXT, hash TEXT, baski TEXT, "
                      "taban_fiyat INTEGER, seq NUMERIC);")
try:
    eski_db.execute("SELECT id, hash, baski, taban_fiyat, seq FROM urunler")
    olcum_f5 = True
except sqlite3.Error:
    olcum_f5 = False
try:
    eski_db.execute("SELECT id, hash, baski, taban_fiyat, seq, marka_arama FROM urunler")
    kolonlu_patlar = False
except sqlite3.Error:
    kolonlu_patlar = True
dogrula("F5 FIILI SINAMA (sqlite): kolonsuz tabloda KOSULLU SELECT calisir, kolonu ISTEYEN "
        "SELECT 'no such column' ile duser (kosul olmasaydi HERKESIN push'u kirilirdi)",
        olcum_f5 and kolonlu_patlar)
eski_db.close()

# ── sonuc ───────────────────────────────────────────────────────────────────────
if ATLANAN:
    print("\nOLCULEMEDI (beyan):")
    for s in ATLANAN:
        print("  - " + s)
print("\nNE OLCULMEDI (beyan):")
print("  1. CANLI UC KODU. Worker `/ara` BU DEPODA DEGIL (pruvo-bot, HocA). Bu test kolonun")
print("     DOGRU DOLDUGUNU olcer; ucun onu OKUDUGUNU olcmez. O eksen HocA'nin kapisidir.")
print("  2. CANLI D1'DEKI DEGER. Test yerel sqlite ikizinde olcer; canlida ne yazdigi")
print("     `python3 tools/d1-sync.py --durum` ile olculur (ALTER canliya UYGULANMADI).")
print("  3. `?q=` SORGUSUNUN MARKA ADI OLDUGU YARGISI. Kolon 'hangi urun' sorusunu cevaplar,")
print("     'bu dizge marka mi' sorusunu CEVAPLAMAZ. Olculdu (5 Agu): DISTINCT kolon degeri")
print("     146 aday marka adinin 129'unu cozer; kalan 17'nin 16'si URUNSUZ markadir")
print("     (site de 0 dondurur), 1'i ALIAS'tir: 'Vauxhall' -> 'Opel' (493 urun).")
print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
sys.exit(1 if kalan[0] else 0)
