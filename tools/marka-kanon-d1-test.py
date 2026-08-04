#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — D1 `marka_kanon` kolonu (kanonik marka uyeligi) DOGRU doluyor mu?

  python3 tools/marka-kanon-d1-test.py

SORUN (olculen SESSIZ hata, 4 Agu 2026 — musteri urunu KAYBEDIYOR, alarm YOK):
uctaki (Worker) `?marka=` kolu `marka` kolonunda HAM STRING ESITLIGI ariyor; site ise
markayi KATLIYOR (index.html markaKatla). 128 kanonik markanin 9'unda cip ile sayfa
AYRISIYOR ve 120 urun-kalemi cipe basildiginda KAYBOLUYOR (canli olcum: Volvo sayfa 726 ·
cip 620; Citroen 4, Opel 3, IKEA 2, Datsun/Smart/Kia/Mini/Black+Decker 1'er).

COZUM (bu testin olctugu sey): katlama mantigi Worker'a KOPYALANMAZ (ikinci govde =
[[ikiz-tanim-sessiz-ayrisma]]); kanonik uyelik SENKRON ANINDA deponun TEK KAYNAGINDAN
(marka_model_build.marka_uyelikleri — ana sayfa filtresinin ta kendisi) turetilip D1'e
ONCEDEN yazilir. Uc yalnizca hazir degeri okur.

🔴 BU TESTIN ASIL SAYISI (C bolumu): sqlite ikizinde kolon doldurulunca, kanonik uyelikle
sayilan marka adedi ile MARKA SAYFASININ adedi 128/128 BIREBIR olur ve ham-esitlikteki
120 kalemlik kayip KAPANIR. Iddia EZBERDEN degil, gercek katalogdan olculur.

Bu test CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek tools/d1-sema.sql'i yerel bir
sqlite3'e yukler, gercek d1-sync fonksiyonlarini (marka_kanon_haritasi, marka_kanon_plan)
ve gercek urunler.json'u kullanir.

MUTASYON GUARDI (G): sonda marka_kanon_plan MONKEYPATCH ile no-op yapilip senaryonun
GERCEKTEN kirmiziya dondugu kanitlanir (yesil test dogru seyi olcuyor mu).
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
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def trigram_var_mi():
    """CI ubuntu'nun stok sqlite3'unde fts5-trigram YOK (bkz. konfigur-d1-test.py ayni
    olcum). Bu testin iddialari FTS'e IHTIYAC DUYMAZ; kabiliyet OLCULUR, muafiyet yazilmaz."""
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
    """d1-sema.sql; trigram yoksa FTS5 sanal tablosu + ona bagli tetikler CIKARILIR.
    (Bolme kurali konfigur-d1-test.py ile AYNI: tetik -> `END;`, digerleri -> `;`.)"""
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


# ── kaynaklar ───────────────────────────────────────────────────────────────────
d1 = yukle_modul("d1_sync_mk", "d1-sync.py")
import arama                                                       # noqa: E402
import marka_model_build as mmb                                    # noqa: E402

URUNLER = json.load(open(os.path.join(KOK, "urunler.json"), encoding="utf-8"))
INDEX = open(os.path.join(KOK, "index.html"), encoding="utf-8").read()

# CAPALAR: kapinin (tools/marka-invaryant-kapisi.py) POZITIF CAPALARI ile AYNI urunler.
# Her biri KATLAMA OLMADAN uye OLAMAZ: `marka` dizisi kanonik adi HAM olarak TASIMAZ.
CAPALAR = [
    ("sierra-hava-filtresi-18-7908", "Volvo"),
    ("peugeot-citroen-2-pinli-elektrik-konnektoru", "Citroen"),
    ("black-decker-zimpara-vakum-adaptoru", "Black+Decker"),
    ("hyundai-ve-kia-g-s-paneli-klipsi", "Kia"),
    ("datsun-mido-far-arka-kapagi", "Datsun"),
]


def sema_kolonlari(metin, tablo):
    m = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?%s\s*\((.*?)\n\);" % tablo,
                  metin, re.S)
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


# ══ A) IKIZ TANIM — kolon dogru SINIFTA mi ═══════════════════════════════════════
print("\n[A] IKIZ TANIM — kolon nerede tanimli, hangi senkron sinifinda")
sema = sema_kolonlari(open(SEMA, encoding="utf-8").read(), "urunler")
goc = dict(d1.GOC_KOLON)
kt = sema_kolonlari(d1._KT_SEMA, "urunler")
ins = re.search(r"INSERT INTO urunler \(([^)]*)\)",
                d1.satir_sql({"id": "a", "marka": []}, 1, "hs", "h")).group(1).split(",")
dogrula("A1 `marka_kanon` d1-sema.sql CREATE TABLE'da (temiz DB ayni semayi alir)",
        sema.get("marka_kanon") == "TEXT", sema.get("marka_kanon"))
dogrula("A2 `marka_kanon` GOC_KOLON'da (canli tablo ALTER ile alir)",
        "marka_kanon" in goc, sorted(goc))
dogrula("A3 GOC_KOLON DEFAULT'u '[]' ('' DEGIL — okuma ucu JSON.parse'i kosulsuz uygular)",
        "'[]'" in goc.get("marka_kanon", ""), goc.get("marka_kanon"))
dogrula("A4 `marka_kanon` _KT_SEMA'da (offline fikstur canli semadan AYRISMAZ)",
        kt.get("marka_kanon") == "TEXT", kt.get("marka_kanon"))
# 🔴 SINIF: hash'e KARISMAZ -> icerik upsert'inde OLMAMALI. Deger yalnizca urunun `marka`
# dizisine degil, index.html KURATORLUGUNE de bagli; icerik upsert'ine baglansaydi yeni bir
# marka TANINMIS listeye eklendiginde hicbir hash degismez ve kolon SONSUZA DEK bayat kalirdi.
dogrula("A5 `marka_kanon` satir_sql INSERT listesinde DEGIL (hedefli UPDATE sinifi)",
        "marka_kanon" not in [k.strip() for k in ins], ins)
dogrula("A6 `marka_kanon` KOLONLAR'da DEGIL (ON CONFLICT yolu ona DOKUNMAZ)",
        "marka_kanon" not in d1.KOLONLAR)

# ══ B) TURETIM — deger MARKA SAYFASI UYELIGININ TA KENDISI mi ════════════════════
print("\n[B] TURETIM — tek kaynak + capalar")
harita, sebep = d1.marka_kanon_haritasi(URUNLER)
dogrula("B1 turetim BASARILI (sebep None; fail-closed dalina DUSMEDI)", sebep is None, sebep)
degerler = set()
for v in harita.values():
    degerler.update(json.loads(v))
dogrula("B2 harita DOLU: %d urun, %d ayri kanonik marka degeri"
        % (len(harita), len(degerler)), len(harita) > 1000 and len(degerler) > 100,
        "%d / %d" % (len(harita), len(degerler)))

# CAPA: kolon TAM OLARAK ham esitligin KACIRDIGINI ekliyor mu.
for pid, marka in CAPALAR:
    urun = next((p for p in URUNLER if p.get("id") == pid), None)
    if urun is None:
        dogrula("B3 CAPA %s katalogda VAR" % pid, False, "urun bulunamadi")
        continue
    kanon = json.loads(harita.get(pid, "[]"))
    dogrula("B3 CAPA %s: HAM `marka` dizisi '%s' TASIMAZ (katlama SART)" % (pid, marka),
            marka not in (urun.get("marka") or []), str(urun.get("marka")))
    dogrula("B4 CAPA %s: marka_kanon '%s' ICERIR (kayip kalem kurtarildi)" % (pid, marka),
            marka in kanon, str(kanon))

# ══ C) SQLITE IKIZI — 120 KALEMLIK KAYIP GERCEKTEN KAPANIYOR MU ══════════════════
print("\n[C] SQLITE IKIZI — retrofit + kanonik sayim MARKA SAYFASIYLA birebir mi")
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
bos = conn.execute("SELECT COUNT(*) c FROM urunler WHERE marka_kanon='[]'").fetchone()["c"]
dogrula("C1 retrofit ONCESI: TUM satirlar D1 varsayilaninda ('[]') — %d" % bos,
        bos == conn.execute("SELECT COUNT(*) c FROM urunler").fetchone()["c"])

mevcut = {r["id"]: r["marka_kanon"] for r in
          conn.execute("SELECT id, marka_kanon FROM urunler")}
plan = d1.marka_kanon_plan(URUNLER, harita, mevcut)
dogrula("C2 plan TAM %d UPDATE uretir (markasiz urune DOKUNMAZ — olcek kapisi)" % len(harita),
        len(plan) == len(harita), "plan=%d harita=%d" % (len(plan), len(harita)))
for sql in plan:
    conn.executescript(sql)
conn.commit()

# Kanonik sayim: uc bu kolonu boyle okuyacak.
json1 = json1_var_mi(conn)
evren = mmb.MarkaEvreni(INDEX)
ek = mmb.cip_evreni_markalari(URUNLER, INDEX)
veri = mmb.gruplandir(URUNLER, evren, ek)
sayfa_adet = {m: mmb.marka_urun_sayisi(d) for m, d in veri.items()}

if json1:
    def kanon_say(marka):
        return conn.execute(
            "SELECT COUNT(*) c FROM urunler WHERE EXISTS "
            "(SELECT 1 FROM json_each(urunler.marka_kanon) WHERE value = ?)",
            (marka,)).fetchone()["c"]
else:
    ATLANAN.append("sqlite JSON1 yok -> kanonik sayim SQL yerine Python tarafinda okundu "
                   "(kolonun ICERIGI ayni; yalniz SORGU BICIMI olculmedi)")

    def kanon_say(marka):
        n = 0
        for r in conn.execute("SELECT marka_kanon FROM urunler"):
            if marka in json.loads(r["marka_kanon"]):
                n += 1
        return n


def ham_say(marka):
    """UCUN BUGUNKU YUKLEMI — ham string esitligi (katlama YOK)."""
    n = 0
    for r in conn.execute("SELECT marka FROM urunler"):
        if marka in json.loads(r["marka"]):
            n += 1
    return n


sapan = [(m, sayfa_adet[m], kanon_say(m)) for m in veri if kanon_say(m) != sayfa_adet[m]]
dogrula("C3 🔴 kanonik sayim = MARKA SAYFASI adedi, %d/%d markada BIREBIR (sapan: %s)"
        % (len(veri) - len(sapan), len(veri), sapan[:4]), not sapan)

kurtarilan = {m: sayfa_adet[m] - ham_say(m) for m in veri if sayfa_adet[m] != ham_say(m)}
dogrula("C4 🔴 ham esitligin KACIRDIGI %d kalem (%d marka) kolonla KURTARILDI: %s"
        % (sum(kurtarilan.values()), len(kurtarilan),
           sorted(kurtarilan.items(), key=lambda t: -t[1])[:4]),
        sum(kurtarilan.values()) >= 100 and all(
            kanon_say(m) == sayfa_adet[m] for m in kurtarilan))
dogrula("C5 ornek — Volvo: sayfa %d · HAM esitlik %d · marka_kanon %d"
        % (sayfa_adet.get("Volvo", 0), ham_say("Volvo"), kanon_say("Volvo")),
        kanon_say("Volvo") == sayfa_adet.get("Volvo") > ham_say("Volvo"))

# ══ D) IDEMPOTENS + OLCEK ════════════════════════════════════════════════════════
print("\n[D] IDEMPOTENS + OLCEK")
mevcut2 = {r["id"]: r["marka_kanon"] for r in
           conn.execute("SELECT id, marka_kanon FROM urunler")}
dogrula("D1 idempotent: D1 zaten dogruysa 0 UPDATE (her push'ta thrash YOK)",
        d1.marka_kanon_plan(URUNLER, harita, mevcut2) == [])
markasiz = [p for p in URUNLER if not (p.get("marka") or [])]
dogrula("D2 markasiz %d urune HIC dokunulmaz (hedef '[]' = D1 varsayilani)" % len(markasiz),
        d1.marka_kanon_plan(markasiz, harita, {}) == [])
# 🔴 VARSAYILAN EKSENI — AYIRT EDICI FIKSTUR: D1'deki GERCEK hal '[]'dir (kolonun DEFAULT'u).
# varsayilan='[]' ile hedef == mevcut -> 0 UPDATE; varsayilan='' (sema_plan'in eski sabiti)
# ile hedef '' != '[]' -> markasiz HER urune 1 bos UPDATE. Fikstur '[]' TASIMASAYDI iki
# cagri da 0 doner ve bu eksen SESSIZCE olculmez olurdu ([[fikstur-degeri-mutasyon-koru]]).
d1_hali = {p["id"]: "[]" for p in markasiz[:50]}
dogrula("D3 sema_plan varsayilani '[]' ile cagriliyor (yoksa markasiz urunlerin HEPSINE "
        "bos UPDATE dogardi)",
        d1.sema_plan("marka_kanon", markasiz[:50], {}, d1_hali, None, varsayilan="[]") == []
        and len(d1.sema_plan("marka_kanon", markasiz[:50], {}, d1_hali, None)) == 50,
        "%d / %d" % (len(d1.sema_plan("marka_kanon", markasiz[:50], {}, d1_hali, None,
                                      varsayilan="[]")),
                     len(d1.sema_plan("marka_kanon", markasiz[:50], {}, d1_hali, None))))

# ══ E) FAIL-CLOSED — "BOSALT" DEGIL "DOKUNMA" ════════════════════════════════════
print("\n[E] FAIL-CLOSED — tek kaynak okunamazsa kolon BOSALTILMAZ")
_gercek_kok = d1.KOK
try:
    d1.KOK = os.path.join(KOK, "tools", "fikstur", "__yok__")
    bos_harita, bos_sebep = d1.marka_kanon_haritasi(URUNLER)
    dogrula("E1 index.html okunamayinca SEBEP doner (sessiz bos harita YOK)",
            bos_sebep is not None and bos_harita == {}, str(bos_sebep))
finally:
    d1.KOK = _gercek_kok
dogrula("E2 sebep DOLUYKEN main plani KOSMAZ — kaynak metinde kosul VAR",
        "not marka_kanon_sebep" in open(os.path.join(TOOLS, "d1-sync.py"),
                                        encoding="utf-8").read())
# Bos harita ile plan kosulsaydi ne olurdu: TUM katalog '[]' olurdu. Olculur.
zarar = d1.marka_kanon_plan(URUNLER, {}, mevcut2)
dogrula("E3 (kontrfaktuel) bos harita ile kosulsaydi %d satir '[]' YAPILIRDI — bu yuzden "
        "atlanir" % len(zarar), len(zarar) == len(harita))

# ══ F) SEMA SIRASI — kolonu SELECT eden kod ONCE push'lanabilir mi ══════════════
print("\n[F] SEMA SIRASI — 'no such column' ile herkesin push'unu kirma riski")
kaynak = open(os.path.join(TOOLS, "d1-sync.py"), encoding="utf-8").read()
dogrula("F1 d1_mevcut SELECT'i marka_kanon'u KOSULLU ekler (kolon yoksa istemez)",
        '", marka_kanon" if marka_kanon_kolonu else ""' in kaynak)
dogrula("F2 kolon varligi PRAGMA'dan okunur (tablo_kolonlari)",
        '"marka_kanon" in tablo_kolonlari' in kaynak)
dogrula("F3 marka_kanon ZORUNLU_KOLONLAR'da DEGIL (yoklugu senkronu DUSURMEZ)",
        "marka_kanon" not in d1.ZORUNLU_KOLONLAR, d1.ZORUNLU_KOLONLAR)

# ══ G) MUTASYON GUARDI — bu test dogru seyi mi olcuyor ═══════════════════════════
print("\n[G] MUTASYON GUARDI — plan no-op yapilinca senaryo KIRMIZI olmali")
conn2 = yeni_db()
conn2.row_factory = sqlite3.Row
for i, p in enumerate(URUNLER):
    if not p.get("id"):
        continue
    conn2.execute("INSERT INTO urunler (rid,id,hash,seq,baslik,kategori,marka,hs) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (i + 1, p["id"], "h", len(URUNLER) - i, "", "",
                   json.dumps(p.get("marka") or [], ensure_ascii=False), ""))
conn2.commit()
_orijinal = d1.marka_kanon_plan
try:
    d1.marka_kanon_plan = lambda *a, **k: []       # MUTASYON: hedefli UPDATE'i kaldir
    for sql in d1.marka_kanon_plan(URUNLER, harita, {}):
        conn2.executescript(sql)
    conn2.commit()
    kalan_bos = conn2.execute(
        "SELECT COUNT(*) c FROM urunler WHERE marka_kanon='[]'").fetchone()["c"]
    dogrula("G1 MUTASYON KANITI: plan no-op -> %d satir '[]' KALIR (nobetci calisiyor)"
            % kalan_bos,
            kalan_bos == conn2.execute("SELECT COUNT(*) c FROM urunler").fetchone()["c"])
finally:
    d1.marka_kanon_plan = _orijinal

# ── sonuc ───────────────────────────────────────────────────────────────────────
if ATLANAN:
    print("\nOLCULEMEDI (beyan):")
    for s in ATLANAN:
        print("  - " + s)
print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
sys.exit(1 if kalan[0] else 0)
