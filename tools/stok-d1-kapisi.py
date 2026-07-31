#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — TICARI HAL (`tur` / `stokta`) D1 hattinda SESSIZ YANLIS VAAT uretemez.

  python3 tools/stok-d1-kapisi.py              # kabul (CI'da bloklayici)
  python3 tools/stok-d1-kapisi.py --mutasyon   # cift yonlu mutasyon (elle; ~10 kosum)
  python3 tools/stok-d1-kapisi.py --kok /yol   # semayi/modulleri BASKA bir agactan oku

NEDEN VAR (HocA olcumu, 31 Tem): katalogda `tur:"fiziksel"` (hazir ticari mal — boya,
vernik, maskeleme bandi) isaretli kayitlar var; bunlar 3D baskiyla URETILMEZ, fiyati
SABITTIR ve TUKENIR. Bu ayrim D1'de HIC YOKTU -> Ege (WhatsApp botu katalogu D1'DEN okur)
fiziksel urunu ya hic goremiyor ya da "size uretiriz" diyordu.

BU KAPININ OLCTUGU DORT SESSIZ-HATA SINIFI (hepsi "site dogru gosterir, Ege yanlis soyler"):
  A TIP        `stokta` TEXT olursa SQLite tamsayi 0'i '0' METNINE cevirir; uc taraf JS'tir
               ve Boolean('0') === true -> TUKENMIS urun STOKTA diye sunulur. Kolon INTEGER
               olmali VE geri-okumada gercekten tamsayi donmeli.
  B HASH       `tur`/`stokta` urun_hash'e girmezse "tukendi" isareti hash'i degistirmez,
               diff-upsert satiri "degismemis" sayar ve D1'e HIC YAZMAZ -> eski stok hali
               KALICILASIR. (taban_fiyat/konfigur'un tam TERSI karar: onlar hash'e KOR ve
               hedefli UPDATE ile gider, cunku ikisi de hash'e girseydi content-thrash
               uretirdi; tur/stokta ise PUBLIC urunler.json'da yasar ve icerik alanidir.)
  C IKIZ TANIM Ayni tablo UC yerde tanimli: tools/d1-sema.sql (canli), d1-sync.GOC_KOLON
               (goc), d1-sync._KT_SEMA (offline fikstur) — ustune bir de satir_sql'in INSERT
               listesi ve KOLONLAR (ON CONFLICT). Biri otekinden ayrisirsa testler YESIL
               yanarken canli baska semayla kosar. Bu eksen bes tanimi BIRBIRINE bagli
               invaryantlarla kilitler (tek kaynaga indirgenemeyen yerde invaryant sarti).
  D FAIL-CLOSED Alan YOKKEN uretilen deger "STOKTA" DIYEMEZ. `stokta` UC DEGERLIDIR:
               -1 BILINMIYOR (alan yok) · 0 STOKTA DEGIL (alan var, true degil) · 1 STOKTA.
               Ikili yapilsaydi "alan hic yok" ile "acikca tukendi" ayni hucreye duser ve
               15.930 ozel uretim urunu ya topluca TUKENMIS ilan edilir ya da gercekten
               tukenmis fiziksel urun satilirdi.
  E VERI       Gercek katalogta taninmayan yazim ("Fiziksel", "true" metni) ya da STOK
               BILGISIZ fiziksel urun kalmasin (o urun Ege'de sessizce fail-closed'a duser).

CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek tools/d1-sema.sql yerel bir sqlite3
kopyasina yuklenir, gercek d1-sync fonksiyonlari (satir_sql, diff_plan) ve gercek
arama.urun_hash kullanilir. Fiksturler SENTETIKTIR (gercek kisisel veri YOK) ama gercek
kayit SEKLINI taklit eder. E ekseni yalniz urunler.json'un ticari-hal ALANLARINI okur.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

GERCEK_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def yukle(kok, ad, dosya):
    """tools/<dosya>'yi MODUL olarak yukle (kok parametrik -> mutasyon kopyasi da olculur)."""
    spec = importlib.util.spec_from_file_location(ad, os.path.join(kok, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


# ── SEMA AYRISTIRICI ────────────────────────────────────────────────────────────────
# CREATE TABLE govdesini kolon ADI -> TIP sozlugune cevirir. Yorum satirlari (-- ...)
# atilir; d1-sema.sql'de kolon aciklamalari kolon tanimindan UZUN oldugu icin sart.
_KOLON_RE = re.compile(r"^([a-z_][a-z0-9_]*)\s+([A-Z]+)")


def sema_kolonlari(metin, tablo):
    """CREATE TABLE <tablo> govdesindeki {kolon: TIP}. Bulunamazsa bos sozluk."""
    m = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?%s\s*\(" % re.escape(tablo), metin)
    if not m:
        return {}
    i = m.end()
    derinlik = 1
    govde = []
    while i < len(metin) and derinlik > 0:
        ch = metin[i]
        if ch == "(":
            derinlik += 1
        elif ch == ")":
            derinlik -= 1
            if derinlik == 0:
                break
        govde.append(ch)
        i += 1
    satirlar = []
    for satir in "".join(govde).splitlines():
        satir = satir.split("--")[0].strip()
        if satir:
            satirlar.append(satir)
    out = {}
    for parca in " ".join(satirlar).split(","):
        km = _KOLON_RE.match(parca.strip())
        if km:
            out[km.group(1)] = km.group(2)
    return out


def insert_kolonlari(sql):
    """satir_sql ciktisindaki INSERT kolon listesi (sirali)."""
    m = re.search(r"INSERT INTO urunler \(([^)]*)\) VALUES", sql)
    return [k.strip() for k in m.group(1).split(",")] if m else []


def conflict_kolonlari(sql):
    """satir_sql ciktisindaki ON CONFLICT ... DO UPDATE SET kolonlari (FIILEN guncellenen)."""
    m = re.search(r"DO UPDATE SET (.*);\s*$", sql, re.S)
    if not m:
        return []
    return [p.split("=")[0].strip() for p in m.group(1).split(",") if "=" in p]


def js_dogru(v):
    """JS Boolean(v) taklidi — uc tarafin `if (satir.stokta)` davranisi.
    ONEMLI: JS'te Boolean('0') === true (bos olmayan her metin dogrudur)."""
    if isinstance(v, str):
        return v != ""
    return bool(v)


# ── FIKSTURLER — gercek kayit SEKLI, sentetik icerik ────────────────────────────────
def _urun(uid, **ek):
    """Gercek urunler.json kaydinin sekli (alan adlari + tipleri birebir), icerigi sentetik."""
    u = {
        "id": uid,
        "kategori": "Marin",
        "marka": [],
        "baslik": "Sinama Urunu %s" % uid,
        "aciklama": "Sinama aciklamasi.\nYaklasik dis olculer: 10 x 20 x 30 mm",
        "fiyat": "200 TL",
        "gorseller": ["https://media.example/urunler/%s-1.jpg" % uid],
    }
    u.update(ek)
    return u


def _tabloyu_kur(sema_metni):
    """d1-sema.sql'i bellekte sqlite'a yukle. FTS5 trigram bu derlemede yoksa yalniz
    `urunler` tablosu kurulur (kapinin olctugu eksenler FTS'e bagli DEGIL)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(sema_metni)
    except sqlite3.Error:
        # FTS5/trigram yok -> sanal tablo + tetikleyicileri at, tablo tanimi AYNEN kalsin.
        temiz = re.sub(r"CREATE VIRTUAL TABLE.*?;", "", sema_metni, flags=re.S)
        temiz = re.sub(r"CREATE TRIGGER.*?END;", "", temiz, flags=re.S)
        temiz = re.sub(r"DROP TRIGGER[^;]*;", "", temiz)
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(temiz)
    return conn


def kabul(kok):
    sema_yolu = os.path.join(kok, "tools", "d1-sema.sql")
    with open(sema_yolu, encoding="utf-8") as f:
        sema_metni = f.read()
    arama = yukle(kok, "arama", "arama.py")
    d1 = yukle(kok, "d1_sync_kapi", "d1-sync.py")
    sema = sema_kolonlari(sema_metni, "urunler")
    goc = dict(d1.GOC_KOLON)
    kt_sema = sema_kolonlari(d1._KT_SEMA, "urunler")

    ornek_sql = d1.satir_sql(_urun("a", tur="fiziksel", stokta=True), 1,
                             arama.haystack(_urun("a")), "H")
    ins = insert_kolonlari(ornek_sql)
    conf = conflict_kolonlari(ornek_sql)

    # ══ A EKSENI — TIP (yanlis tip = musteriye yanlis vaat) ════════════════════════
    print("\n[A] TIP — `stokta` INTEGER mi (TEXT olursa JS'te '0' TRUE okunur)")
    dogrula("A1 d1-sema.sql: stokta INTEGER", sema.get("stokta") == "INTEGER",
            "bulunan: %r" % sema.get("stokta"))
    dogrula("A2 GOC_KOLON (canli ALTER): stokta INTEGER ile baslar",
            (goc.get("stokta") or "").startswith("INTEGER"), "bulunan: %r" % goc.get("stokta"))
    dogrula("A3 tur kolonu TEXT (metin hali; 'fiziksel' / '')", sema.get("tur") == "TEXT",
            "bulunan: %r" % sema.get("tur"))

    conn = _tabloyu_kur(sema_metni)
    pragma = {s["name"]: s["type"] for s in conn.execute("PRAGMA table_info(urunler)")}
    dogrula("A4 PRAGMA table_info(urunler): stokta tipi INTEGER (gercek sema yuklendi)",
            pragma.get("stokta") == "INTEGER", "bulunan: %r" % pragma.get("stokta"))

    # ROUND-TRIP: gercek satir_sql ile yaz, geri oku, TIPI olc.
    for uid, urun, beklenen in (
            ("stok-var", _urun("stok-var", tur="fiziksel", stokta=True), 1),
            ("stok-yok", _urun("stok-yok", tur="fiziksel", stokta=False), 0),
            ("stok-bilinmiyor", _urun("stok-bilinmiyor"), -1)):
        conn.executescript(d1.satir_sql(urun, 1, arama.haystack(urun), "H%s" % uid))
    okunan = {s["id"]: s["stokta"] for s in conn.execute("SELECT id, stokta FROM urunler")}
    dogrula("A5 GERI-OKUMA TIPI: uc satirin da stokta degeri int (metin DEGIL)",
            all(type(okunan[k]) is int for k in okunan), {k: repr(v) for k, v in okunan.items()})
    dogrula("A6 GERI-OKUMA DEGERI: true->1 · false->0 · alan yok->-1",
            okunan.get("stok-var") == 1 and okunan.get("stok-yok") == 0
            and okunan.get("stok-bilinmiyor") == -1, okunan)
    dogrula("A7 JS EKSENI: tukenmis urun uc tarafta YANLIS-DOGRU okunmuyor "
            "(Boolean(deger) False)", js_dogru(okunan.get("stok-yok")) is False,
            "deger %r -> JS %s" % (okunan.get("stok-yok"), js_dogru(okunan.get("stok-yok"))))
    dogrula("A8 JS EKSENI NEGATIF NOBETI: ayni deger METIN olsaydi JS TRUE okurdu "
            "(iddia bos degil)", js_dogru("0") is True)
    # SQL LITERAL EKSENI: deger TIRNAKSIZ (tamsayi sabiti) yazilmali. INTEGER affinity
    # '0' metnini bugun sessizce 0'a cevirdigi icin geri-okuma bunu YAKALAYAMAZ — ama
    # affinity kolona baglidir: sema bir gun (baska bir yoldan kurulan tablo, drift eden
    # goc) TEXT'e kayarsa tirnakli yazim o gun yanlis vaadi URETIR. Iki savunma bagimsiz
    # olmali; bu yuzden literal bicimi AYRICA capalanir.
    lit = re.search(r"'fiziksel',([^,]+),0\) ON CONFLICT", ornek_sql)
    dogrula("A9 SQL LITERALI: stokta TIRNAKSIZ tamsayi olarak yaziliyor (q() ile DEGIL)",
            lit is not None and "'" not in lit.group(1)
            and re.fullmatch(r"-?\d+", lit.group(1).strip()) is not None,
            lit.group(1) if lit else "VALUES kuyrugu eslesmedi: " + ornek_sql[-120:])

    # ══ B EKSENI — HASH KAPSAMI (kapsamazsa satir HIC yazilmaz) ═══════════════════
    print("\n[B] HASH — `tur`/`stokta` degisimi satiri D1'e YENIDEN YAZDIRIYOR mu")
    h_ozel = arama.urun_hash(_urun("a"))
    h_fiz = arama.urun_hash(_urun("a", tur="fiziksel", stokta=True))
    h_tuk = arama.urun_hash(_urun("a", tur="fiziksel", stokta=False))
    h_bilinmez = arama.urun_hash(_urun("a", tur="fiziksel"))
    # 🔴 TEK DEGISKEN: yalniz `tur` oynatilir (stokta IKISINDE DE yok). Iki alani birlikte
    # degistiren bir capa, tur hash'ten TAMAMEN cikarilsa bile stokta sayesinde YESIL
    # kalirdi — mutasyonda olculdu (M04 hayatta kalmisti).
    dogrula("B1 SADECE `tur` degisimi hash'i DEGISTIRIR (ozel uretim -> fiziksel)",
            h_ozel != h_bilinmez)
    dogrula("B1b `tur` + `stokta` birlikte degisince de hash DEGISIR", h_ozel != h_fiz)
    dogrula("B2 `stokta` true->false hash'i DEGISTIRIR (TUKENDI isareti D1'e gider)",
            h_fiz != h_tuk)
    dogrula("B3 'bilinmiyor' ile 'stokta degil' AYRI hash uretir (uc hal korunuyor)",
            h_bilinmez != h_tuk and h_bilinmez != h_fiz)
    dogrula("B4 YANLIS-POZITIF NOBETI: ilgisiz alan (gorsel sirasi disi) degismeden hash AYNI",
            arama.urun_hash(_urun("a")) == h_ozel)

    # diff_plan: D1'de VAR olan bir urunun stok isareti degisince UPDATE uretilmeli.
    onceki = _urun("a", tur="fiziksel", stokta=True)
    sonraki = _urun("a", tur="fiziksel", stokta=False)
    yeni, degisen, _, silinen, _ = d1.diff_plan(
        [sonraki], {"a": (arama.urun_hash(onceki), "")}, {}, False, 1, {"a": 1})
    dogrula("B5 diff_plan: TUKENDI isareti 1 'degisen' upsert uretir (0 degil)",
            len(degisen) == 1 and not yeni and not silinen,
            "yeni=%d degisen=%d silinen=%d" % (len(yeni), len(degisen), len(silinen)))
    dogrula("B6 uretilen upsert ON CONFLICT yolunda stokta'yi GUNCELLER",
            "stokta=excluded.stokta" in (degisen[0] if degisen else ""))

    # UCTAN UCA: satir yaz (stokta=1) -> ayni id'yi tukenmis olarak tekrar yaz -> 0 olmali.
    conn2 = _tabloyu_kur(sema_metni)
    conn2.executescript(d1.satir_sql(onceki, 1, arama.haystack(onceki),
                                     arama.urun_hash(onceki)))
    ilk = conn2.execute("SELECT stokta FROM urunler WHERE id='a'").fetchone()["stokta"]
    conn2.executescript(d1.satir_sql(sonraki, 0, arama.haystack(sonraki),
                                     arama.urun_hash(sonraki)))
    son = conn2.execute("SELECT stokta FROM urunler WHERE id='a'").fetchone()["stokta"]
    dogrula("B7 UCTAN UCA: mevcut satirda 1 -> upsert sonrasi 0 (ON CONFLICT FIILEN yaziyor)",
            ilk == 1 and son == 0, "ilk=%r son=%r" % (ilk, son))

    # ══ C EKSENI — IKIZ TANIM INVARYANTI (bes tanim ayrisamaz) ════════════════════
    print("\n[C] IKIZ TANIM — sema / GOC_KOLON / _KT_SEMA / INSERT / KOLONLAR kilidi")
    goc_eksik = [k for k in goc if k not in sema]
    dogrula("C1 GOC_KOLON'daki her kolon d1-sema.sql'de de VAR (temiz DB ayni semayi alir)",
            not goc_eksik, goc_eksik)
    ins_eksik = [k for k in ins if k not in sema]
    dogrula("C2 satir_sql INSERT'inin her kolonu semada VAR (canlida 'no such column' yok)",
            not ins_eksik, ins_eksik)
    kol_eksik = [k for k in d1.KOLONLAR if k not in ins]
    dogrula("C3 KOLONLAR ⊆ INSERT listesi (excluded.<k> ancak yazilan kolondan okunur)",
            not kol_eksik, kol_eksik)
    fark = [k for k in ins if k not in d1.KOLONLAR]
    dogrula("C4 INSERT − KOLONLAR == KASITLI_DISARIDA (yeni kolon sessizce upsert DISI kalamaz)",
            sorted(fark) == sorted(d1.KASITLI_DISARIDA),
            "fark=%s kasitli=%s" % (sorted(fark), sorted(d1.KASITLI_DISARIDA)))
    dogrula("C5 KASITLI_DISARIDA'nin her girisinde GEREKCE var (bos muafiyet yok)",
            all((v or "").strip() for v in d1.KASITLI_DISARIDA.values()))
    dogrula("C6 ON CONFLICT SET listesi == KOLONLAR (uretilen SQL sabitle ayrismiyor)",
            sorted(conf) == sorted(d1.KOLONLAR), "sql=%s" % sorted(conf))
    kt_fark = set(sema) ^ set(kt_sema)
    dogrula("C7 offline fikstur semasi (_KT_SEMA) == d1-sema.sql kolon kumesi",
            not kt_fark, sorted(kt_fark))
    for alan in ("tur", "stokta"):
        dogrula("C8 `%s` BES tanimin hepsinde (sema · GOC · _KT_SEMA · INSERT · KOLONLAR)" % alan,
                alan in sema and alan in goc and alan in kt_sema
                and alan in ins and alan in d1.KOLONLAR,
                "sema=%s goc=%s kt=%s ins=%s kol=%s"
                % (alan in sema, alan in goc, alan in kt_sema, alan in ins,
                   alan in d1.KOLONLAR))
    dogrula("C9 ZORUNLU_KOLONLAR tur+stokta'yi kapsiyor (sema eskiyse senkron FAIL-LOUD)",
            {"tur", "stokta"} <= set(d1.ZORUNLU_KOLONLAR), d1.ZORUNLU_KOLONLAR)
    dogrula("C10 geri-okuma (write-verify) tur+stokta'yi da dogruluyor",
            {"tur", "stokta"} <= set(d1.GERI_OKUMA_KOLONLARI), d1.GERI_OKUMA_KOLONLARI)

    # ══ D EKSENI — FAIL-CLOSED VARSAYILAN ═════════════════════════════════════════
    print("\n[D] FAIL-CLOSED — alan YOKKEN / bozukken 'STOKTA' DENEMEZ")
    dogrula("D1 alan YOK -> STOK_BILINMIYOR (-1), 'stokta degil' (0) DEGIL",
            arama.stokta_kanonik(_urun("a")) == arama.STOK_BILINMIYOR)
    dogrula("D2 alan YOK -> tur '' (OZEL URETIM; katalogun varsayilani)",
            arama.tur_kanonik(_urun("a")) == "")
    dogrula("D3 boolean true -> STOK_VAR (1); tek 'stokta' diyebilen deger",
            arama.stokta_kanonik(_urun("a", stokta=True)) == arama.STOK_VAR)
    dogrula("D4 boolean false -> STOK_YOK (0)",
            arama.stokta_kanonik(_urun("a", stokta=False)) == arama.STOK_YOK)
    # TANINMAYAN degerlerin HICBIRI 1 uretemez. `1` ve `"true"` ozellikle tehlikeli:
    # naif kod (`if u.get("stokta")`) ikisini de STOKTA sayar.
    tehlikeli = ["true", "TRUE", "1", "evet", "var", 1, 2, "0", "false", 0, None, [], {},
                 [True], {"stokta": True}, " ", "stokta"]
    sapan = [repr(v) for v in tehlikeli
             if arama.stokta_kanonik(_urun("a", stokta=v)) == arama.STOK_VAR]
    dogrula("D5 TANINMAYAN 17 deger (metin 'true', sayi 1, dizi...) -> HICBIRI STOK_VAR degil",
            not sapan, sapan)
    yanlis_bilinmiyor = [repr(v) for v in tehlikeli
                         if arama.stokta_kanonik(_urun("a", stokta=v))
                         != arama.STOK_YOK]
    dogrula("D6 TANINMAYAN deger 'BILINMIYOR'a DEGIL 'STOKTA DEGIL'e duser "
            "(alan VAR; emin degilsek satmayiz)", not yanlis_bilinmiyor, yanlis_bilinmiyor)
    tur_sapan = [repr(v) for v in ["3d", "Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ",
                                   "", None, 0, 1, True, False, [], ["fiziksel"],
                                   {"t": "fiziksel"}]
                 if arama.tur_kanonik(_urun("a", tur=v)) != ""]
    dogrula("D7 TANINMAYAN 14 `tur` degeri -> '' (build.py render_product N2 kurali ile AYNI)",
            not tur_sapan, tur_sapan)
    dogrula("D8 'STOKTA' diyebilen deger kumesi TAM OLARAK {1}",
            set(arama.STOK_VAAT_EDILEBILIR) == {1}, arama.STOK_VAAT_EDILEBILIR)
    dogrula("D9 GOC penceresi fail-closed: ALTER DEFAULT'u -1 (0 olsaydi goc anindan "
            "senkrona kadar TUM katalog 'tukenmis' olurdu)",
            "DEFAULT -1" in (goc.get("stokta") or ""), goc.get("stokta"))
    bos = _tabloyu_kur(sema_metni)
    bos.execute("INSERT INTO urunler (rid,id,hash,seq,baslik,kategori,hs) "
                "VALUES (1,'x','H',1,'B','Marin','h')")
    varsayilan = bos.execute("SELECT tur, stokta FROM urunler WHERE id='x'").fetchone()
    dogrula("D10 SEMA VARSAYILANI: kolonu yazmayan bir INSERT -1/'' verir (STOKTA DOGMAZ)",
            varsayilan["stokta"] == -1 and varsayilan["tur"] == "",
            dict(varsayilan))

    # ══ E EKSENI — GERCEK KATALOG VERISI ══════════════════════════════════════════
    print("\n[E] VERI — gercek katalogta taninmayan yazim / stok bilgisiz fiziksel urun")
    urunler_yolu = os.path.join(kok, "urunler.json")
    with open(urunler_yolu, encoding="utf-8") as f:
        katalog = json.load(f)
    kotu_tur, kotu_stok, stoksuz_fiziksel = [], [], []
    fiziksel = stok_var = 0
    for u in katalog:
        if not isinstance(u, dict):
            continue
        uid = u.get("id") or "<id yok>"
        if "tur" in u:
            if u["tur"] != "fiziksel":
                kotu_tur.append((uid, repr(u["tur"])))
            else:
                fiziksel += 1
                if "stokta" not in u:
                    stoksuz_fiziksel.append(uid)
        if "stokta" in u and not isinstance(u["stokta"], bool):
            kotu_stok.append((uid, repr(u["stokta"])))
        if arama.stokta_kanonik(u) == arama.STOK_VAR:
            stok_var += 1
    dogrula("E1 `tur` alani olan her kayit TAM 'fiziksel' (taninmayan yazim yok)",
            not kotu_tur, kotu_tur[:5])
    dogrula("E2 `stokta` alani olan her kayit GERCEK boolean ('true' metni degil)",
            not kotu_stok, kotu_stok[:5])
    dogrula("E3 fiziksel urunlerin HEPSINDE `stokta` alani var "
            "(yoksa Ege o urunde stok VAAT EDEMEZ)", not stoksuz_fiziksel,
            stoksuz_fiziksel[:5])
    print("  OLCUM: %d kayit · fiziksel %d · STOK_VAR (1) uretecek %d · ozel uretim %d"
          % (len(katalog), fiziksel, stok_var, len(katalog) - fiziksel))
    return 0 if kalan[0] == 0 else 1


# ── CIFT YONLU MUTASYON ─────────────────────────────────────────────────────────────
# Her mutant DAR bir probe: yalnizca ilgili iddianin yakalayabilecegi bir bozulma.
# KIRMIZI beklenen = oldurucu mutant · YESIL beklenen = ILGISIZ degisiklik (kapinin
# gereginden genis olmadiginin kaniti — yanlis-pozitif herkesin push'unu kirar).
MUTANTLAR = [
    ("d1-sema.sql", "stokta    INTEGER NOT NULL DEFAULT -1",
     "stokta    TEXT NOT NULL DEFAULT '-1'", "KIRMIZI",
     "A: kolon TEXT olur -> JS'te '0' TRUE okunur (tukenmis urun STOKTA gorunur)"),
    ("d1-sync.py", '("stokta", "INTEGER NOT NULL DEFAULT -1")',
     '("stokta", "TEXT NOT NULL DEFAULT \'-1\'")', "KIRMIZI",
     "A: canli ALTER kolonu TEXT kurar (sema dosyasi dogru olsa BILE)"),
    ("d1-sync.py", '("stokta", "INTEGER NOT NULL DEFAULT -1")',
     '("stokta", "INTEGER NOT NULL DEFAULT 0")', "KIRMIZI",
     "D: goc penceresinde TUM katalog 'stokta degil' olur"),
    ("arama.py", "        tur_kanonik(u),\n", "", "KIRMIZI",
     "B: tur hash'ten cikar -> fiziksel isareti D1'e HIC yazilmaz"),
    ("arama.py", "        stokta_kanonik(u),\n", "", "KIRMIZI",
     "B: stokta hash'ten cikar -> TUKENDI isareti D1'e HIC yazilmaz"),
    ("d1-sync.py", '    "tur", "stokta",\n', '    "tur",\n', "KIRMIZI",
     "C/B: stokta ON CONFLICT disi kalir -> mevcut satirda stok ESKI degerde donar"),
    ("arama.py", "        return STOK_BILINMIYOR", "        return STOK_VAR", "KIRMIZI",
     "D: alan YOKKEN 'STOKTA' denir (fail-open)"),
    ("arama.py", 'return STOK_VAR if u.get("stokta") is True else STOK_YOK',
     'return STOK_VAR if u.get("stokta") else STOK_YOK', "KIRMIZI",
     "D: naif truthy -> 'true' metni ve sayi 1 STOKTA sayilir"),
    ("arama.py", 'return _TUR_FIZIKSEL if u.get("tur") == _TUR_FIZIKSEL else ""',
     'return u.get("tur") or ""', "KIRMIZI",
     "D: ham deger yazilir -> 'Fiziksel'/'3d' D1'e sizar (fail-closed kalkar)"),
    ("d1-sync.py", "str(arama.stokta_kanonik(u))", "q(arama.stokta_kanonik(u))", "KIRMIZI",
     "A: deger TIRNAKLI yazilir -> INTEGER kolona '0' METNI girer"),
    ("d1-sync.py", "  stokta INTEGER NOT NULL DEFAULT -1\n", "", "KIRMIZI",
     "C: offline fikstur semasi canli semadan AYRISIR (ikiz tanim drift'i)"),
    ("d1-sync.py", "TAM_OKUMA_ESIGI = 800", "TAM_OKUMA_ESIGI = 900", "YESIL",
     "ILGISIZ: geri-okuma olcek esigi — ticari hal iddialarina DOKUNMAZ"),
    ("d1-sema.sql", "-- Kurulum: python3 tools/d1-sync.py --sema",
     "-- Kurulum: python3 tools/d1-sync.py --sema   (ilgisiz yorum degisikligi)", "YESIL",
     "ILGISIZ: sema dosyasinda yorum — kapi metne DEGIL yapiya bakiyor"),
]

KOPYALANAN = ["arama.py", "d1-sync.py", "d1-sema.sql", "konfigur-bundle-kapisi.py"]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    basarisiz = []
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = tempfile.mkdtemp(prefix="pruvo-stok-mut-")
        os.makedirs(os.path.join(tmp, "tools"))
        for ad in KOPYALANAN:
            shutil.copy2(os.path.join(GERCEK_KOK, "tools", ad),
                         os.path.join(tmp, "tools", ad))
        # urunler.json 14 MB: KOPYALANMAZ, sembolik baglanir (E ekseni yine olculur).
        os.symlink(os.path.join(GERCEK_KOK, "urunler.json"),
                   os.path.join(tmp, "urunler.json"))
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        if metin.count(eski) != 1:
            basarisiz.append("M%02d capa BULUNAMADI/COKLU (%d kez): %s"
                             % (i, metin.count(eski), eski[:60]))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni))
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                           capture_output=True, text=True)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        isaret = "OK  " if goruldu == beklenen else "HATA"
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        print("  %s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
              % (isaret, i, beklenen, dosya, goruldu, len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:150])
        shutil.rmtree(tmp, ignore_errors=True)

    sonra = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    bozuk = [d for d in once if once[d] != sonra[d]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU (%d oldurucu KIRMIZI + %d ilgisiz YESIL)"
          % (len(MUTANTLAR), len(MUTANTLAR),
             sum(1 for m in MUTANTLAR if m[3] == "KIRMIZI"),
             sum(1 for m in MUTANTLAR if m[3] == "YESIL")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK,
                    help="olculecek agacin koku (mutasyon kopyasi icin)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon (elle kosulur; CI'da degil)")
    a = ap.parse_args()
    if a.mutasyon:
        sys.exit(mutasyon())
    kod = kabul(a.kok)
    print("\nSONUC: %d gecti, %d kaldi%s"
          % (gecen[0], kalan[0], " — HEPSI YESIL" if not kalan[0] else ""))
    sys.exit(kod)


if __name__ == "__main__":
    main()
