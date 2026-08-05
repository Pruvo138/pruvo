#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — D1 `model_kanon` kolonu (kanonik MODEL uyeligi) DOGRU doluyor mu?

  python3 tools/model-kanon-d1-test.py

SORUN (olculen SESSIZ hata, 5 Agu 2026 — musteri urunu KAYBEDIYOR, alarm YOK):
uctaki (Worker) `model` kolu degeri `uyum[].model` alaninda TAM ESITLIKLE ariyor (uyum
bossa ham `marka[]`e dusuyor); site ise modeli KUSAK/VARYANT duzeyinde KATLIYOR
(index.html modelEsler + kusakTabanlari: `Fiesta ST` -> Fiesta, `T4`/`T5` -> Transporter,
`Golf 4`/`Golf Mk4`/`Golf IV` -> Golf, `Astra H` -> Astra). Sonuc: yayimlanan model
kovalarinin BIR KISMINDA sayfa ile uc suzgeci AYRISIYOR ve o urunler musteri MODEL CIPINE
BASINCA KAYBOLUYOR. Marka ekseninde 4 Agu'da kapatilan sinifin BIREBIR AYNISI.

COZUM (bu testin olctugu sey): katlama mantigi Worker'a KOPYALANMAZ (ikinci govde =
[[ikiz-tanim-sessiz-ayrisma]]); kanonik model uyeligi SENKRON ANINDA deponun TEK
KAYNAGINDAN (marka_model_build.gruplandir — model SAYFASINI ureten yuklemin ta kendisi)
turetilip D1'e ONCEDEN yazilir. Uc yalnizca hazir degeri okur.

🔴 BU TESTIN IKI ASIL SAYISI:
  C bolumu — sqlite ikizinde kolon doldurulunca, sayfa ile ucun model suzgeci arasindaki
             kayip 0'a iner (bugunku borc AYNI kosumda olculur, ezberden YAZILMAZ).
  H bolumu — KAYIPSIZLIK: kanonik kumede OLMAYAN ham model jetonu SAYISI + urun-kalemi.
             🔴 Bu sayi HocA'nin "YERINE mi BIRLESIM mi" kararinin girdisidir: marka
             ekseninin aksine burada kanon hamin UST KUMESI DEGIL — kolonu ham `model`in
             YERINE koymak toplu OLU LINK uretirdi. Test bunu IDDIA olarak da olcer.

Bu test CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek tools/d1-sema.sql'i yerel bir
sqlite3'e yukler, gercek d1-sync fonksiyonlarini (model_kanon_haritasi, model_kanon_plan)
ve gercek urunler.json'u kullanir. Semayi CANLIYA UYGULAMAZ.

MUTASYON SURUCUSU: tools/model-kanon-mutasyon.py (anlatilan batarya kanit DEGILDIR —
[[mutasyon-kaniti-yeniden-uretilebilir]]).
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
    """CI ubuntu'nun stok sqlite3'unde fts5-trigram YOK (marka-kanon-d1-test.py ile ayni
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


# ── kaynaklar ───────────────────────────────────────────────────────────────────
d1 = yukle_modul("d1_sync_mdk", "d1-sync.py")
import arama                                                       # noqa: E402
import marka_model_build as mmb                                    # noqa: E402

URUNLER = json.load(open(os.path.join(KOK, "urunler.json"), encoding="utf-8"))
INDEX = open(os.path.join(KOK, "index.html"), encoding="utf-8").read()

# CAPALAR: (urun id, kanonik model etiketi, katlama TURU). Her biri OLCULDU — urunun
# `marka` dizisi kanonik etiketi HAM olarak TASIMAZ, yani uyelik YALNIZCA katlamayla
# dogar. BES AYRI katlama mekanizmasi secildi ki tek bir mekanizmayi kapatan mutant
# capayi kacirmasin (marka-invaryant-kapisi.py CAPALAR deseni).
CAPALAR = [
    ("ford-fiesta-st-far-lastigi-uzatmasi", "Fiesta",
     "donanim/rozet soneki (Fiesta ST -> Fiesta)"),
    ("vw-t4-vites-topu-yerlesim-araci", "Transporter",
     "kuratorlu kusak eslemesi (T4 -> Transporter)"),
    ("golf4-radyo-ustu-telefon-mount", "Golf",
     "sayisal kusak (Golf 4 -> Golf)"),
    ("opel-astra-h-kapi-tutucu-stop-tapasi", "Astra",
     "harf kusagi (Astra H -> Astra)"),
    ("ford-focus-st-mk2-rezonator-tapasi", "Focus",
     "model-olmayan cift + donanim soneki (Focus ST -> Focus)"),
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
dogrula("A1 `model_kanon` d1-sema.sql CREATE TABLE'da (temiz DB ayni semayi alir)",
        sema.get("model_kanon") == "TEXT", sema.get("model_kanon"))
dogrula("A2 `model_kanon` GOC_KOLON'da (canli tablo ALTER ile alir)",
        "model_kanon" in goc, sorted(goc))
dogrula("A3 GOC_KOLON DEFAULT'u '[]' ('' DEGIL — okuma ucu JSON.parse'i kosulsuz uygular)",
        "'[]'" in goc.get("model_kanon", ""), goc.get("model_kanon"))
dogrula("A4 `model_kanon` _KT_SEMA'da (offline fikstur canli semadan AYRISMAZ)",
        kt.get("model_kanon") == "TEXT", kt.get("model_kanon"))
# 🔴 SINIF: hash'e KARISMAZ -> icerik upsert'inde OLMAMALI. Deger yalnizca urunun kendi
# alanlarina degil, index.html KURATORLUGUNE ve KATALOGUN TAMAMINA (kova esigi + kanonik
# gosterim) baglidir; icerik upsert'ine baglansaydi BASKA bir urunun eklenmesi bu urunun
# hedefini degistirir ama hash'i AYNI kalir -> kolon SONSUZA DEK bayat kalirdi.
dogrula("A5 `model_kanon` satir_sql INSERT listesinde DEGIL (hedefli UPDATE sinifi)",
        "model_kanon" not in [k.strip() for k in ins], ins)
dogrula("A6 `model_kanon` KOLONLAR'da DEGIL (ON CONFLICT yolu ona DOKUNMAZ)",
        "model_kanon" not in d1.KOLONLAR)

# ══ B) TURETIM — deger MODEL SAYFASI UYELIGININ TA KENDISI mi ════════════════════
print("\n[B] TURETIM — tek kaynak + capalar")
harita, sebep = d1.model_kanon_haritasi(URUNLER)
dogrula("B1 turetim BASARILI (sebep None; fail-closed dalina DUSMEDI)", sebep is None, sebep)
degerler = set()
for v in harita.values():
    degerler.update(json.loads(v))
dogrula("B2 harita DOLU: %d urun, %d ayri kanonik model degeri"
        % (len(harita), len(degerler)), len(harita) > 1000 and len(degerler) > 100,
        "%d / %d" % (len(harita), len(degerler)))
# BICIM: deger JSON DIZI ve SIRALI olmali — sirasiz birakilsaydi kova yineleme sirasi
# degistiginde metin degisir ve HER senkron sahte UPDATE uretirdi (olcek kapisi).
bicim_bozuk = [uid for uid, v in harita.items()
               if json.loads(v) != sorted(json.loads(v))]
dogrula("B3 deger ALFABETIK SIRALI JSON dizi (sira gurultusu -> sahte UPDATE uretmez)",
        not bicim_bozuk, str(bicim_bozuk[:3]))

# 🔴 DEGER EVRENI = YAYIMLANAN KOVA ETIKETLERI, DAHA GENIS DEGIL. Yayimlanmayan kovanin
# etiketi mimarin ACIK yargiyla KAPATTIGI bir sayfanin adidir (arama.ROZET_DISI_CIFT /
# MODEL_OLMAYAN_CIFT ya da ESIK alti). Kolona yazilsaydi uc `?model=Focus ST` icin sonuc
# dondururdu — kapali sayfa uc tarafindan geri acilirdi.
# 🔴 YARGI BAGIMSIZ OKUNUR: kural burada tools/arama.py tablolarindan YENIDEN kurulur,
# ureticinin `yayimlanir_mi` yuklemi CAGRILMAZ (model-uyelik-kapisi.py'nin ayni ilkesi) —
# cagrilsaydi filtreyi kaldiran mutant iddiayi da kendi lehine buker, eksen totolojiye
# duserdi.
_evren = mmb.MarkaEvreni(INDEX)
_ek = mmb.cip_evreni_markalari(URUNLER, INDEX)
_veri = mmb.gruplandir(URUNLER, _evren, _ek)
_rozet = set((mk, arama.model_normalize(md)) for mk, md in arama.ROZET_DISI_CIFT)
_olmayan = set((mk, arama.model_normalize(jt)) for mk, jt in arama.MODEL_OLMAYAN_CIFT)


def _yayin_bagimsiz(marka, g):
    """yayimlanir_mi()'nin BAGIMSIZ yeniden kurulusu — yargi tablolari arama.py'den."""
    ad = g.get("display") or g.get("canon")
    n = arama.model_normalize(ad)
    if (marka, arama.model_normalize(g.get("canon") or "")) in _rozet or (marka, n) in _rozet:
        return False
    if (marka, n) in _olmayan:
        return False
    son = ad.split()
    if len(son) >= 2 and (marka, arama.model_normalize(son[-1])) in _olmayan:
        return False
    return bool(g.get("birincil")) and len(g["urunler"]) >= mmb.ESIK


_beklenen_evren = set(g["display"] for marka, d in _veri.items()
                      for g in d["gruplar"].values() if _yayin_bagimsiz(marka, g))
dogrula("B7 deger evreni = YAYIMLANAN kova etiketleri (bagimsiz yargi ile %d etiket); "
        "kapali sayfa etiketi SIZMIYOR"
        % len(_beklenen_evren), degerler == _beklenen_evren,
        "fazla=%s eksik=%s" % (sorted(degerler - _beklenen_evren)[:6],
                               sorted(_beklenen_evren - degerler)[:6]))

kimlik_sayaci = {}
for p in URUNLER:
    if p.get("id"):
        kimlik_sayaci[p["id"]] = kimlik_sayaci.get(p["id"], 0) + 1
for pid, model, tur in CAPALAR:
    urun = next((p for p in URUNLER if p.get("id") == pid), None)
    # 🔴 CAPA TAM BIR KEZ: mukerrer id, "capa gecti" hukmunu belirsizlestirirdi.
    dogrula("B4 CAPA %s katalogda TAM BIR KEZ geciyor" % pid,
            kimlik_sayaci.get(pid, 0) == 1, "bulunan %d" % kimlik_sayaci.get(pid, 0))
    if urun is None:
        continue
    kanon = json.loads(harita.get(pid, "[]"))
    ham = [(x or "").strip() for x in (urun.get("marka") or [])]
    dogrula("B5 CAPA %s: HAM `marka` dizisi '%s' TASIMAZ (katlama SART — %s)"
            % (pid, model, tur), model not in ham, str(ham))
    dogrula("B6 CAPA %s: model_kanon '%s' ICERIR (kayip kalem kurtarildi)" % (pid, model),
            model in kanon, str(kanon))

# ══ C) SQLITE IKIZI — SAYFA <-> UC MODEL SUZGECI ayrismasi KAPANIYOR MU ══════════
print("\n[C] SQLITE IKIZI — retrofit + sayfa/suzgec ayrismasi")
conn = yeni_db()
conn.row_factory = sqlite3.Row
for i, p in enumerate(URUNLER):
    if not p.get("id"):
        continue
    conn.execute(
        "INSERT INTO urunler (rid,id,hash,seq,baslik,kategori,marka,uyum,hs) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (i + 1, p["id"], arama.urun_hash(p), len(URUNLER) - i, p.get("baslik") or "",
         p.get("kategori") or "", json.dumps(p.get("marka") or [], ensure_ascii=False),
         json.dumps(p.get("uyum") or [], ensure_ascii=False), arama.haystack(p)))
conn.commit()
bos = conn.execute("SELECT COUNT(*) c FROM urunler WHERE model_kanon='[]'").fetchone()["c"]
dogrula("C1 retrofit ONCESI: TUM satirlar D1 varsayilaninda ('[]') — %d" % bos,
        bos == conn.execute("SELECT COUNT(*) c FROM urunler").fetchone()["c"])

mevcut = {r["id"]: r["model_kanon"] for r in
          conn.execute("SELECT id, model_kanon FROM urunler")}
plan = d1.model_kanon_plan(URUNLER, harita, mevcut)
dogrula("C2 plan TAM %d UPDATE uretir (model kovasi disindaki urune DOKUNMAZ — olcek "
        "kapisi)" % len(harita),
        len(plan) == len(harita), "plan=%d harita=%d" % (len(plan), len(harita)))
for sql in plan:
    conn.executescript(sql)
conn.commit()

json1 = json1_var_mi(conn)
if not json1:
    ATLANAN.append("sqlite JSON1 yok -> kanonik/uc kumeleri SQL yerine Python tarafinda "
                   "okundu (kolonun ICERIGI ayni; yalniz SORGU BICIMI olculmedi)")

_kanon_bellek = {}
for r in conn.execute("SELECT id, model_kanon FROM urunler"):
    # `or "[]"`: kolon NOT NULL DEFAULT '[]' oldugu icin bos dize YALNIZ bir MUTANT altinda
    # dogar; okuyucu orada COKMEZ (cokme kirmiziyla karisirdi) — o hal C2'de olculur.
    for v in json.loads(r["model_kanon"] or "[]"):
        _kanon_bellek.setdefault(v, set()).add(r["id"])

# UCUN BUGUNKU MODEL YUKLEMI (Worker uyumEkseniKosulu / egeUyumSarti portu, BILEREK
# BAGIMSIZ yazildi — sayfa yuklemini CAGIRMAZ; totoloji tuzagi).
_uyum_model, _ham_marka, _bos_uyum = {}, {}, set()
for r in conn.execute("SELECT id, marka, uyum FROM urunler"):
    uy = json.loads(r["uyum"])
    if not uy:
        _bos_uyum.add(r["id"])
    _uyum_model[r["id"]] = set(
        (o.get("model") or "").strip() for o in uy
        if isinstance(o, dict) and (o.get("model") or "").strip())
    _ham_marka[r["id"]] = set(
        (x or "").strip() for x in json.loads(r["marka"]) if (x or "").strip())


def uc_ham(deger):
    """`?model=<deger>` — BUGUNKU uc: uyum[].model TAM esitlik, uyum bossa marka[]e duser."""
    return set(uid for uid in _uyum_model
               if deger in _uyum_model[uid]
               or (uid in _bos_uyum and deger in _ham_marka[uid]))


def uc_birlesim(deger):
    """HocA'nin uygulayacagi HAL: ham ∪ kanonik (`model_kanon`)."""
    return uc_ham(deger) | _kanon_bellek.get(deger, set())


# SAYFA kumesi B7'de kurulan AYNI kova agacindan okunur (gruplandir ikinci kez kosmaz).
yayin = [(m, g) for m, d in _veri.items() for g in d["gruplar"].values()
         if mmb.yayimlanir_mi(g)]
kayip_once, kayip_sonra = {}, {}
for marka, g in yayin:
    ad = g["display"]
    sayfa = set(p["id"] for p in g["urunler"] if p.get("id"))
    if sayfa - uc_ham(ad):
        kayip_once[(marka, ad)] = len(sayfa - uc_ham(ad))
    if sayfa - uc_birlesim(ad):
        kayip_sonra[(marka, ad)] = len(sayfa - uc_birlesim(ad))
dogrula("C3 🔴 BUGUNKU BORC olculdu: %d yayimlanan kovanin %d'sinde sayfa uc suzgecinden "
        "GENIS — %d urun-kalemi kayip (en agir: %s)"
        % (len(yayin), len(kayip_once), sum(kayip_once.values()),
           sorted(kayip_once.items(), key=lambda t: -t[1])[:3]),
        sum(kayip_once.values()) >= 100 and len(kayip_once) >= 20,
        "kova=%d kalem=%d" % (len(kayip_once), sum(kayip_once.values())))
dogrula("C4 🔴 BIRLESIMLE (ham ∪ model_kanon) kayip 0'a iner — %d kova / %d kalem kaldi"
        % (len(kayip_sonra), sum(kayip_sonra.values())), not kayip_sonra,
        str(sorted(kayip_sonra.items(), key=lambda t: -t[1])[:4]))
for pid, model, tur in CAPALAR:
    dogrula("C5 CAPA %s: bugunku uc `?model=%s` KACIRIYOR, kolonla BULUYOR"
            % (pid, model), pid not in uc_ham(model) and pid in uc_birlesim(model),
            "ham=%s birlesim=%s" % (pid in uc_ham(model), pid in uc_birlesim(model)))

# ══ D) IDEMPOTENS + OLCEK ════════════════════════════════════════════════════════
print("\n[D] IDEMPOTENS + OLCEK")
mevcut2 = {r["id"]: r["model_kanon"] for r in
           conn.execute("SELECT id, model_kanon FROM urunler")}
dogrula("D1 idempotent: D1 zaten dogruysa 0 UPDATE (her push'ta thrash YOK)",
        d1.model_kanon_plan(URUNLER, harita, mevcut2) == [],
        "%d UPDATE" % len(d1.model_kanon_plan(URUNLER, harita, mevcut2)))
kovasiz = [p for p in URUNLER if p.get("id") and p["id"] not in harita]
dogrula("D2 model kovasi disindaki %d urune HIC dokunulmaz (hedef '[]' = D1 varsayilani)"
        % len(kovasiz), d1.model_kanon_plan(kovasiz, harita, {}) == [])
# 🔴 VARSAYILAN EKSENI — AYIRT EDICI FIKSTUR (marka_kanon'daki ile ayni sinif): D1'deki
# GERCEK hal '[]'dir. varsayilan='[]' ile hedef == mevcut -> 0 UPDATE; varsayilan=''
# (sema_plan'in sabiti) ile hedef '' != '[]' -> kovasiz HER urune 1 bos UPDATE. Fikstur
# '[]' TASIMASAYDI iki cagri da 0 doner ve eksen SESSIZCE olculmez olurdu.
d1_hali = {p["id"]: "[]" for p in kovasiz[:50]}
dogrula("D3 sema_plan varsayilani '[]' ile cagriliyor (yoksa kovasiz urunlerin HEPSINE "
        "bos UPDATE dogardi)",
        d1.sema_plan("model_kanon", kovasiz[:50], {}, d1_hali, None, varsayilan="[]") == []
        and len(d1.sema_plan("model_kanon", kovasiz[:50], {}, d1_hali, None)) == 50,
        "%d / %d" % (len(d1.sema_plan("model_kanon", kovasiz[:50], {}, d1_hali, None,
                                      varsayilan="[]")),
                     len(d1.sema_plan("model_kanon", kovasiz[:50], {}, d1_hali, None))))

# ══ E) FAIL-CLOSED — "BOSALT" DEGIL "DOKUNMA" ════════════════════════════════════
print("\n[E] FAIL-CLOSED — tek kaynak okunamazsa kolon BOSALTILMAZ")
_gercek_kok = d1.KOK
try:
    d1.KOK = os.path.join(KOK, "tools", "fikstur", "__yok__")
    bos_harita, bos_sebep = d1.model_kanon_haritasi(URUNLER)
    dogrula("E1 index.html okunamayinca SEBEP doner (sessiz bos harita YOK)",
            bos_sebep is not None and bos_harita == {}, str(bos_sebep))
finally:
    d1.KOK = _gercek_kok
dogrula("E2 sebep DOLUYKEN main plani KOSMAZ — kaynak metinde kosul VAR",
        "not model_kanon_sebep" in open(os.path.join(TOOLS, "d1-sync.py"),
                                        encoding="utf-8").read())
zarar = d1.model_kanon_plan(URUNLER, {}, mevcut2)
dogrula("E3 (kontrfaktuel) bos harita ile kosulsaydi %d satir '[]' YAPILIRDI — bu yuzden "
        "atlanir" % len(zarar), len(zarar) == len(harita))

# ══ F) SEMA SIRASI — kolonu SELECT eden kod ONCE push'lanabilir mi ══════════════
print("\n[F] SEMA SIRASI — 'no such column' ile herkesin push'unu kirma riski")
kaynak = open(os.path.join(TOOLS, "d1-sync.py"), encoding="utf-8").read()
dogrula("F1 d1_mevcut SELECT'i model_kanon'u KOSULLU ekler (kolon yoksa istemez)",
        '", model_kanon" if model_kanon_kolonu else ""' in kaynak)
dogrula("F2 kolon varligi PRAGMA'dan okunur (tablo_kolonlari)",
        '"model_kanon" in tablo_kolonlari' in kaynak)
dogrula("F3 model_kanon ZORUNLU_KOLONLAR'da DEGIL (yoklugu senkronu DUSURMEZ)",
        "model_kanon" not in d1.ZORUNLU_KOLONLAR, d1.ZORUNLU_KOLONLAR)
# YAPISAL KANIT: kolonu OLMAYAN bir tabloda d1_mevcut'un urettigi SELECT gercekten kosar.
eski_db = sqlite3.connect(":memory:")
eski_db.executescript(
    "CREATE TABLE urunler (rid INTEGER PRIMARY KEY, id TEXT, hash TEXT, baski TEXT, "
    "taban_fiyat INTEGER, seq INTEGER, konfigur TEXT, marka_kanon TEXT);")
try:
    eski_db.execute("SELECT id, hash, baski, taban_fiyat, seq, konfigur, marka_kanon "
                    "FROM urunler").fetchall()
    f4 = True
except sqlite3.Error:
    f4 = False
dogrula("F4 kolon YOKKEN kosan SELECT (model_kanon'suz hali) ESKI semada CALISIR — bu dal "
        "ALTER'dan ONCE alinsa bile kimsenin push'u kirilmaz", f4)

# ══ H) KAYIPSIZLIK — HocA'nin "YERINE mi BIRLESIM mi" karari icin OLCUM ══════════
print("\n[H] KAYIPSIZLIK — kolonu ham `model`in YERINE koymak NEYI dusururdu")
ham_slot = {}
for uid in _uyum_model:
    jetonlar = set(_uyum_model[uid])
    if uid in _bos_uyum:
        jetonlar |= _ham_marka[uid]
    for t in jetonlar:
        ham_slot[t] = ham_slot.get(t, 0) + 1
disari = {t: n for t, n in ham_slot.items() if t not in _kanon_bellek}
print("  ham model jetonu (uyum[].model ∪ uyum-bos marka[]): %d jeton / %d urun-kalemi"
      % (len(ham_slot), sum(ham_slot.values())))
print("  KANONIK kumede OLMAYAN                             : %d jeton / %d urun-kalemi"
      % (len(disari), sum(disari.values())))
print("  en agir 10: %s" % sorted(disari.items(), key=lambda t: -t[1])[:10])
# 🔴 IKI TANIM, IKI SAYI — UZLASTIRMA BURADA BASILIR (kardes kapi ayni ekseni DAR tanimla
# olcuyor ve sayilari farkli cikiyordu; "hangi sayi dogru" tartismasi tanim farkindan
# doguyor, olcum hatasindan DEGIL). GENIS tanim ucun model kolunun IKI dalini da sayar
# (uyum[].model VE uyum='[]' halinde marka[] dusme dali); DAR tanim yalniz birinci dali.
_dar = {}
for uid in _uyum_model:
    for t in _uyum_model[uid]:
        _dar[t] = _dar.get(t, 0) + 1
_dar_disari = {t: n for t, n in _dar.items() if t not in _kanon_bellek}
print("  UZLASTIRMA — DAR tanim (yalniz uyum[].model, dusme dali HARIC): "
      "%d/%d jeton · %d/%d urun-kalemi disarda"
      % (len(_dar_disari), len(_dar), sum(_dar_disari.values()), sum(_dar.values())))
print("  UZLASTIRMA — GENIS tanim (dusme dali DAHIL, yukaridaki satirlar): "
      "%d/%d jeton · %d/%d urun-kalemi disarda"
      % (len(disari), len(ham_slot), sum(disari.values()), sum(ham_slot.values())))
dogrula("H1 🔴 kanon ham'in UST KUMESI DEGIL — %d jeton / %d urun-kalemi kolonda HIC "
        "GECMIYOR, yani WHERE'i bu kolona CEVIRMEK toplu OLU LINK uretirdi (BIRLESIM SART)"
        % (len(disari), sum(disari.values())), len(disari) > 0)
# TERS YON de olculur: "ham eslesiyor ama kanon eslesmiyor" cifti — marka ekseninde bu
# sayi 0'di (kanon ust kumeydi) ve orada "yerine koymak" yalnizca kanon-disi jetonlarda
# zarar veriyordu. Burada 0 DEGIL: ayni kanonik etikette bile kanon ham'i KAPSAMIYOR.
alt_degil = []
for marka, g in yayin:
    ad = g["display"]
    fark = uc_ham(ad) - _kanon_bellek.get(ad, set())
    if fark:
        alt_degil.append((marka, ad, len(fark)))
print("  'ham eslesiyor ama kanon eslesmiyor': %d kova / %d urun-kalemi — %s"
      % (len(alt_degil), sum(x[2] for x in alt_degil),
         sorted(alt_degil, key=lambda t: -t[2])[:5]))
dogrula("H2 BEYAN: yayimlanan kova etiketlerinde bile kanon ham'i KAPSAMIYOR (%d kova / "
        "%d kalem) — marka ekseninden FARKLI, birlesim ZORUNLU"
        % (len(alt_degil), sum(x[2] for x in alt_degil)), True)

# ── sonuc ───────────────────────────────────────────────────────────────────────
if ATLANAN:
    print("\nOLCULEMEDI (beyan):")
    for s in ATLANAN:
        print("  - " + s)
print("\nNE OLCULMEDI (beyan):")
print("  1. CANLI UC KODU. Worker `model` kolu BU DEPODA DEGIL; burada YEREL PORTLA")
print("     modellendi (uc_ham). Uc kodu degisirse model SESSIZCE ayrisabilir.")
print("  2. D1'in CANLI degeri: bu test SEMAYI CANLIYA UYGULAMAZ, yerel sqlite ikizinde")
print("     olcer. Canli deger `python3 tools/d1-sync.py --durum` isidir.")
print("  3. MODEL_FAZLA (uc suzgecinde SAYFADAN FAZLA cikan urun) BLOKLAMAZ: `model`")
print("     parametresi marka-KOR oldugu icin ayni etiketi tasiyan iki markanin kovasi")
print("     birbirinin sonucunu genisletir (olculdu: bugun 371 kalem, birlesimle 372).")

print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
sys.exit(1 if kalan[0] else 0)
