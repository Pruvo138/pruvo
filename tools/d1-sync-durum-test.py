#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — d1-sync.py --durum FAIL-LOUD teyidi.

  python3 tools/d1-sync-durum-test.py

Wrangler/ag/D1 GEREKMEZ: d1-sync importlib ile yuklenir; SAF durum_uyumlu() dogrudan,
--durum cikis kodu ise sorgu() monkeypatch + gecici urunler.json ile SINANIR (canli D1'e
DOKUNMAZ). Amac: D1 sayisi urunler.json'daki benzersiz id sayisiyla UYUMSUZ oldugunda
--durum exit 1 (fail-loud), uyumluysa exit 0 (temiz donus) — 'insan gormeden gecmesin'.
"""
import importlib.util
import json
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

gecen = [0]
kalan = [0]


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


# ── TURETILMIS KOLON EKSENI fikstur uretici govdeleri (SAF, D1'e/aga dokunmaz) ──────
# 🔴 NEDEN FIKSTUR URETICI: --durum'un CIKIS KODU olculurken gercek uretici govdeler
# (marka_arama_haritasi vb.) 20.850 urunluk KATALOGA ve index.html'e bagimlidir; 3 urunluk
# offline fiksturde model_kanon zaten "kova evreni BOS" der. Bu yuzden CIKIS KODU testleri
# EKSEN MAKINESINI fikstur ureticilerle olcer; URETICI GOVDENIN KENDISI ayrica ve GERCEK
# koduyla olculur (bkz. bolum 5, alias ekseni) -> ikisi birlikte hem makineyi hem yuklemi
# kapatir, hicbiri digerinin yerine gecmez.
FIKSTUR_KOLON = "fikstur_kanon"


def fikstur_kayit(hedef_fn, plan_fn=None, kolon=FIKSTUR_KOLON):
    """TURETILMIS_KAYIT bicimli tek girisli kayit defteri."""
    def _plan(urunler, hedefler, mevcut, izleme=None):
        # GERCEK plan govdesi (sema_plan) — kural KOPYALANMAZ.
        return _D1[0].sema_plan(kolon, urunler, hedefler, mevcut, izleme, varsayilan="[]")
    return [{"kolon": kolon, "hedef": hedef_fn, "plan": plan_fn or _plan,
             "coz": "python3 tools/fikstur.py"}]


_D1 = [None]     # modul referansi (fikstur_kayit icindeki plan govdesi icin)


def fake_sorgu_uret(d1_sayisi, d1_hash, seq_haritasi, turetilmis=None, kolonlar=None):
    """sorgu() yerine gecen sahte: COUNT -> d1_sayisi · senkron -> tek satir ·
    ICERIK EKSENI (SELECT id, hash) -> d1_hash haritasi ·
    TURETILMIS EKSEN (PRAGMA table_info + SELECT id, <kolonlar>) -> turetilmis haritasi.
    turetilmis = {id: {kolon: deger}} · kolonlar = CANLI tablonun kolon adlari (kume)."""
    turetilmis = turetilmis or {}
    kolonlar = kolonlar or set()

    def _f(sql):
        if "COUNT(*)" in sql:
            return [{"results": [{"n": d1_sayisi}]}]
        if "senkron" in sql:
            return [{"results": [{"anahtar": "urun_sayisi", "deger": str(d1_sayisi)}]}]
        if "SELECT id, hash FROM urunler" in sql:
            return [{"results": [{"id": i, "hash": h} for i, h in sorted(d1_hash.items())],
                     "meta": {"rows_read": len(d1_hash)}}]
        if sql == "SELECT id, seq FROM urunler":
            return [{"results": [{"id": i, "seq": s} for i, s in seq_haritasi.items()]}]
        if sql.startswith("PRAGMA table_info(urunler)"):
            return [{"results": [{"name": k} for k in sorted(kolonlar)]}]
        if "sqlite_master" in sql:
            # SEMA EKSENI yesil kalsin: kolonlari donduren tablo icin indeksler de VAR.
            return [{"results": [{"name": ix["ad"]} for ix in _D1[0].GOC_INDEKS]}]
        if sql.startswith("SELECT id, ") and "FROM urunler" in sql:
            istenen = [k.strip() for k in
                       sql[len("SELECT id, "):sql.index(" FROM urunler")].split(",")]
            return [{"results": [dict({"id": i}, **{k: (v.get(k) or "") for k in istenen})
                                 for i, v in sorted(turetilmis.items())]}]
        return [{"results": []}]
    return _f


def durum_cikis(d1, urunler_listesi, d1_sayisi, bayat=None, hizli=False,
                kayit=None, turetilmis=None, ek_kolon=()):
    """--durum'u OFFLINE kosar (sorgu + URUNLER monkeypatch), cikis kodunu dondur.
    Donen: 0 = temiz donus (uyumlu) · 1 = sys.exit ile fail-loud (uyumsuz).
    bayat = D1'de hash'i BOZULACAK id (sayi AYNI kalir -> yalniz ICERIK EKSENI gorur).
    hizli = --hizli bayragi (icerik + turetilmis eksenleri ATLANIR).
    kayit = TURETILMIS_KAYIT yerine gecen fikstur defteri (None -> eksen kaydi BOS).
    turetilmis = {id: {kolon: canli deger}} · ek_kolon = canli tabloya SOKULAN fazla kolon
    (kapsam acigi ekseni icin)."""
    _D1[0] = d1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(urunler_listesi, f)
        yol = f.name
    d1_hash = {}
    for u in urunler_listesi:
        if u.get("id") and u["id"] not in d1_hash:
            d1_hash[u["id"]] = d1.arama.urun_hash(u)
    if bayat:
        d1_hash[bayat] = "BAYATHASH"
    kayit = [] if kayit is None else kayit
    kolonlar = (set(d1.HASH_KAPSAMI) | set(d1.EKSEN_DISI)
                | {k["kolon"] for k in kayit} | set(ek_kolon))
    eski_sorgu, eski_urunler, eski_argv = d1.sorgu, d1.URUNLER, sys.argv
    eski_kayit = d1.TURETILMIS_KAYIT
    try:
        d1.sorgu = fake_sorgu_uret(
            d1_sayisi, d1_hash, d1.seq_hedefleri(urunler_listesi), turetilmis, kolonlar)
        d1.URUNLER = yol
        d1.TURETILMIS_KAYIT = kayit
        sys.argv = ["d1-sync.py", "--durum"] + (["--hizli"] if hizli else [])
        try:
            d1.main()
            return 0                       # sys.exit CAGRILMADI -> uyumlu
        except SystemExit as e:
            # sys.exit(str) -> code bir metin (mesaj) = basarisizlik (exit 1);
            # sys.exit(None/0) -> temiz. Kodu POSIX cikis koduna cevir.
            c = e.code
            if c is None or c == 0:
                return 0
            return 1 if not isinstance(c, int) else c
    finally:
        d1.sorgu, d1.URUNLER, sys.argv = eski_sorgu, eski_urunler, eski_argv
        d1.TURETILMIS_KAYIT = eski_kayit
        os.unlink(yol)


def main():
    d1 = yukle_modul("d1_sync", "d1-sync.py")

    # ── (1) SAF durum_uyumlu() — D1'e/dosyaya dokunmadan ──────────────────────
    dogrula("durum_uyumlu esit -> True", d1.durum_uyumlu(100, 100) is True)
    dogrula("durum_uyumlu D1 eksik -> False", d1.durum_uyumlu(99, 100) is False)
    dogrula("durum_uyumlu D1 fazla (silme propage olmadi) -> False",
            d1.durum_uyumlu(101, 100) is False)
    dogrula("durum_uyumlu D1 None (okunamadi) -> False (fail-loud)",
            d1.durum_uyumlu(None, 100) is False)
    dogrula("durum_uyumlu D1 sayisi metin ('100') -> True",
            d1.durum_uyumlu("100", 100) is True)
    dogrula("durum_uyumlu sifir/sifir -> True (bos katalog tutarli)",
            d1.durum_uyumlu(0, 0) is True)

    # ── (2) --durum cikis kodu — sorgu() + URUNLER monkeypatch (D1'e DOKUNMAZ) ──
    # 4 elemanli liste ama 3 BENZERSIZ id ('c' mukerrer) -> beklenen D1 satiri = 3.
    urunler = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "c"}]

    dogrula("--durum UYUMLU (D1=3 == benzersiz 3) -> exit 0",
            durum_cikis(d1, urunler, 3) == 0)
    dogrula("--durum UYUMSUZ (D1=2 < benzersiz 3) -> exit 1 (fail-loud)",
            durum_cikis(d1, urunler, 2) == 1)
    dogrula("--durum UYUMSUZ (D1=4 > benzersiz 3, silme kacti) -> exit 1",
            durum_cikis(d1, urunler, 4) == 1)
    dogrula("--durum mukerrer id LISTE uzunluguyla degil BENZERSIZ ile kiyaslar "
            "(D1=4 == liste uzunlugu ama exit 1)",
            durum_cikis(d1, urunler, 4) == 1)
    dogrula("--durum D1 okunamadi (COUNT None) -> exit 1",
            durum_cikis(d1, urunler, None) == 1)

    # ── (3) ICERIK EKSENI (31 Tem) — SAYI TUTARKEN icerik bayat olabilir ───────
    # OLCULEN OLAY: tek alan degisimi (kategori) D1'e islemedi; satir SAYISI degismedigi
    # icin --durum YESIL yandi ve merge-kapisi'nin zorunlu D1 teyidi bu vakaya KOR kaldi.
    dogrula("--durum ICERIK: sayi TUTUYOR + hash'ler uyumlu -> exit 0",
            durum_cikis(d1, urunler, 3) == 0)
    dogrula("🔴 --durum ICERIK: sayi TUTUYOR ama bir urunun D1 hash'i BAYAT -> exit 1",
            durum_cikis(d1, urunler, 3, bayat="b") == 1)
    dogrula("--durum --hizli: icerik ekseni ATLANIR -> bayat hash'e ragmen exit 0 "
            "(bayrak BEYAN ediyor, sessizce atlamiyor)",
            durum_cikis(d1, urunler, 3, bayat="b", hizli=True) == 0)

    # ══════════════════════════════════════════════════════════════════════════
    # (4) TURETILMIS KOLON EKSENI (6 Agu) — urun_hash'in KAPSAMADIGI kolonlar
    # ══════════════════════════════════════════════════════════════════════════
    # OLCULEN OLAY: canli `marka_arama` kolonunda Honda 1898 iken olmasi gereken 1979 idi
    # (Grom 43 ↔ 44). SAYI tutuyor, SEMA temiz, ICERIK ekseni hash'i kiyasliyor ve hash bu
    # kolonu OZETLEMIYOR -> UC EKSEN DE YESIL. Bu bolum tam o vakayi kirmizi yakar.
    _D1[0] = d1
    KOLON = FIKSTUR_KOLON
    tam = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    def sabit(harita, sebep=None):
        return lambda urunler: (harita, sebep)

    def eksen(hedef_fn, mevcut, kolonlar=(KOLON,), plan_fn=None):
        return d1.turetilmis_eksen(tam, set(kolonlar), {KOLON: mevcut},
                                   kayit=fikstur_kayit(hedef_fn, plan_fn))

    hedef = {"a": '["Honda"]', "b": '["Opel","Vauxhall"]'}
    guncel = dict(hedef, c="[]")

    h = eksen(sabit(hedef), guncel)
    dogrula("TURETILMIS: canli deger uretici govdenin urettigiyle AYNI -> GUNCEL",
            h[0]["hal"] == d1.TK_GUNCEL and h[0]["sayi"] == 0)
    dogrula("TURETILMIS: GUNCEL halde sorun satiri URETILMEZ",
            d1.turetilmis_sorunlari(h) == [])

    h = eksen(sabit(hedef), dict(guncel, b='["Opel"]'))
    dogrula("🔴 TURETILMIS: SAYI + HASH tutarken kolon BAYAT (bir satir eski) -> BAYAT(1)",
            h[0]["hal"] == d1.TK_BAYAT and h[0]["sayi"] == 1)
    dogrula("TURETILMIS: BAYAT sorun satiri KOLON ADINI ve SAYIYI basar",
            len(d1.turetilmis_sorunlari(h)) == 1
            and KOLON in d1.turetilmis_sorunlari(h)[0]
            and "b" in dict(h[0]["ornek"]))

    h = eksen(sabit(hedef), {})
    dogrula("TURETILMIS: canli kolon TOPTAN bos (sema kosmus ama senkron hic yazmamis) "
            "-> BAYAT(2), sessiz GECMEZ",
            h[0]["hal"] == d1.TK_BAYAT and h[0]["sayi"] == 2)

    # ── FAIL-CLOSED: uretilemeyen/olculemeyen hal ASLA yesil sayilmaz ──────────
    h = eksen(sabit(None, "tek kaynak okunamadi"), guncel)
    dogrula("🔴 TURETILMIS: uretici govde SEBEP dondurdu -> OLCULEMEDI (yesil DEGIL)",
            h[0]["hal"] == d1.TK_OLCULEMEDI)
    dogrula("🔴 TURETILMIS: OLCULEMEDI sorun satiri URETIR (fail-closed)",
            len(d1.turetilmis_sorunlari(h)) == 1
            and "OLCULEMEDI" in d1.turetilmis_sorunlari(h)[0])

    def patlat(_urunler):
        raise RuntimeError("uretici govde YOK")

    dogrula("🔴 TURETILMIS: uretici govde ISTISNA atti -> OLCULEMEDI (cokme DEGIL)",
            eksen(patlat, guncel)[0]["hal"] == d1.TK_OLCULEMEDI)

    def cik(_urunler):
        sys.exit("fail-closed tek kaynak")

    dogrula("🔴 TURETILMIS: uretici govde sys.exit etti -> OLCULEMEDI (arac COKMEZ)",
            eksen(cik, guncel)[0]["hal"] == d1.TK_OLCULEMEDI)

    def plan_patlat(_u, _h, _m, _i=None):
        raise RuntimeError("plan govdesi YOK")

    dogrula("🔴 TURETILMIS: PLAN govdesi dustu -> OLCULEMEDI",
            eksen(sabit(hedef), guncel, plan_fn=plan_patlat)[0]["hal"] == d1.TK_OLCULEMEDI)
    dogrula("🔴 TURETILMIS: kolon CANLI tabloda YOK -> OLCULEMEDI (atlanmaz)",
            eksen(sabit(hedef), guncel, kolonlar=())[0]["hal"] == d1.TK_OLCULEMEDI)
    dogrula("🔴 TURETILMIS: canli deger SELECT'ten gelmedi -> OLCULEMEDI",
            d1.turetilmis_eksen(tam, {KOLON}, {}, kayit=fikstur_kayit(sabit(hedef)))[0]["hal"]
            == d1.TK_OLCULEMEDI)

    # ── KAPSAM: hangi kolon hangi eksende — kayitsiz kolon SESSIZ KALAMAZ ──────
    dogrula("KAPSAM: hash kapsami KOLONLAR'dan TURETILIR (ikinci liste yok) — "
            "baslik ICINDE, marka_arama DISINDA",
            "baslik" in d1.HASH_KAPSAMI and "marka_arama" not in d1.HASH_KAPSAMI
            and set(d1.KOLONLAR) <= set(d1.HASH_KAPSAMI))
    canli_kolon = (set(d1.HASH_KAPSAMI) | set(d1.EKSEN_DISI)
                   | {k["kolon"] for k in d1.TURETILMIS_KAYIT})
    dogrula("KAPSAM: bugunku D1 kolonlarinin HEPSI uc kumeden birinde -> acik YOK",
            d1.kapsam_acigi(canli_kolon) == [])
    dogrula("🔴 KAPSAM: canliya SINIFLANDIRILMAMIS yeni kolon girerse acik BASILIR "
            "(marka_arama tam boyle dogmustu)",
            d1.kapsam_acigi(canli_kolon | {"yeni_turetilmis"}) == ["yeni_turetilmis"])
    dogrula("KAPSAM: acik sorun satiri uretir (yesil sayilmaz)",
            len(d1.turetilmis_sorunlari([], ["yeni_turetilmis"])) == 1)
    dogrula("KAPSAM: EKSEN_DISI girisleri GEREKCELI (bos gerekce YOK)",
            all(isinstance(v, str) and len(v) > 20 for v in d1.EKSEN_DISI.values()))
    dogrula("KAPSAM: kayit defteri kolonlari hash kapsamiyla CAKISMAZ "
            "(bir kolon iki eksende sayilmaz)",
            not ({k["kolon"] for k in d1.TURETILMIS_KAYIT} & set(d1.HASH_KAPSAMI)))
    dogrula("KAPSAM: kayit defteri 5 hash-disi turetilmis kolonu tasir",
            {k["kolon"] for k in d1.TURETILMIS_KAYIT}
            == {"konfigur", "taban_fiyat", "marka_kanon", "model_kanon", "marka_arama"})
    dogrula("KAPSAM: kayit defteri GERCEK uretici govdeleri isaret eder (ikinci yuklem yok)",
            [k["hedef"] for k in d1.TURETILMIS_KAYIT][2:]
            == [d1.marka_kanon_haritasi, d1.model_kanon_haritasi, d1.marka_arama_haritasi])

    # ── taban_fiyat: BOS sema = "dokunma" -> eksen bunu YESIL saymamali ────────
    eski_dir = d1.JEN_URUN_DIR
    try:
        d1.JEN_URUN_DIR = os.path.join(KOK, "OLMAYAN-DIZIN")
        _hrt, _sbp = d1.taban_hedefleri(tam)
        dogrula("🔴 TURETILMIS: taban semasi OKUNAMADI -> hedef None + sebep "
                "(taban_plan bos haritada [] doner = sessiz yesil olurdu)",
                _hrt is None and bool(_sbp))
    finally:
        d1.JEN_URUN_DIR = eski_dir

    # ── CIKIS KODU: eksen --durum'a FIILEN bagli mi (makine ucu uca) ───────────
    canli = {"a": {KOLON: '["Honda"]'}, "b": {KOLON: '["Opel","Vauxhall"]'},
             "c": {KOLON: "[]"}}
    dogrula("--durum TURETILMIS: kolon GUNCEL -> exit 0",
            durum_cikis(d1, tam, 3, kayit=fikstur_kayit(sabit(hedef)),
                        turetilmis=canli) == 0)
    dogrula("🔴 --durum TURETILMIS: SAYI TUTUYOR + HASH TUTUYOR ama kolon BAYAT -> exit 1 "
            "(olculen Honda 1898/1979 vakasi)",
            durum_cikis(d1, tam, 3, kayit=fikstur_kayit(sabit(hedef)),
                        turetilmis=dict(canli, b={KOLON: '["Opel"]'})) == 1)
    dogrula("🔴 --durum TURETILMIS: uretici govde URETEMEDI -> exit 1 (OLCULEMEDI)",
            durum_cikis(d1, tam, 3, kayit=fikstur_kayit(sabit(None, "kaynak yok")),
                        turetilmis=canli) == 1)
    dogrula("🔴 --durum KAPSAM: siniflandirilmamis canli kolon -> exit 1",
            durum_cikis(d1, tam, 3, kayit=fikstur_kayit(sabit(hedef)),
                        turetilmis=canli, ek_kolon=("yeni_turetilmis",)) == 1)
    dogrula("--durum --hizli: turetilmis eksen ATLANIR -> bayat kolona ragmen exit 0 "
            "(bayrak BEYAN ediyor, sessizce atlamiyor)",
            durum_cikis(d1, tam, 3, hizli=True, kayit=fikstur_kayit(sabit(hedef)),
                        turetilmis=dict(canli, b={KOLON: '["Opel"]'})) == 0)
    # 🔴 KORELME: yeni eksen eklendi diye ESKI eksenlerin gucu azalmamali.
    dogrula("KORELME: turetilmis eksen GUNCEL iken GERCEK senkron arizasi (urun D1'de YOK) "
            "hala exit 1 (ICERIK + SAYI eksenleri sag)",
            durum_cikis(d1, tam, 2, kayit=fikstur_kayit(sabit(hedef)),
                        turetilmis={i: v for i, v in canli.items() if i != "c"}) == 1)

    # ══════════════════════════════════════════════════════════════════════════
    # (5) URETICI GOVDENIN KENDISI — GERCEK kodla, fikstursuz yuklem ekseni
    # ══════════════════════════════════════════════════════════════════════════
    # 🔴 NEDEN AYRI: (4) EKSEN MAKINESINI olcer, uretici govdeyi fiksturler. Govde
    # `marka[]`den HAM kopyalamaya cevrilse (4) YESIL kalirdi. Bu iddia govdenin
    # KENDISINI kosar: alias kolu index.html MARKA_ALIAS'tan gelir ve KATALOGDAN
    # BAGIMSIZDIR -> kucuk fiksturde de olculebilir. Uc `?q=Vauxhall` sorgusunu yalniz
    # bu kolondan cozer (canlida 493 urun).
    fik = [{"id": "opel-1", "baslik": "Opel Astra Bagaj Kancasi", "marka": ["Opel"],
            "kategori": "Otomobil"}]
    _ma, _sebep = d1.marka_arama_haritasi(fik)
    _deger = json.loads(_ma.get("opel-1") or "[]")
    dogrula("URETICI: marka_arama_haritasi KANONIK adi tasir (Opel)",
            _sebep is None and "Opel" in _deger)
    dogrula("🔴 URETICI: marka_arama_haritasi ALIAS yazimini da tasir (Vauxhall) — "
            "alias kolu duserse uc `?q=Vauxhall`i HIC cozemez",
            _sebep is None and "Vauxhall" in _deger)

    # 🔴 HAM `marka[]` KOPYASI OLAMAZ: alias YAZIMIYLA gelen urunun kolonu KANONIK adi
    # (Opel) tasimali. Ham kopya ["Vauxhall"] verirdi ve o urun `?q=Opel`de KAYBOLURDU —
    # canlida Opel kumesi 493 urun, ham `marka[]`de 'Opel' yalniz 490'inda YAZIYOR.
    fik2 = [{"id": "vaux-1", "baslik": "Vauxhall Corsa Kapi Tamponu",
             "marka": ["Vauxhall"], "kategori": "Otomobil"}]
    _ma2, _sebep2 = d1.marka_arama_haritasi(fik2)
    _deger2 = json.loads(_ma2.get("vaux-1") or "[]")
    dogrula("🔴 URETICI: alias yazimli urun KANONIK adi tasir (Vauxhall -> Opel) — "
            "kolon HAM `marka[]` kopyasi OLAMAZ",
            _sebep2 is None and "Opel" in _deger2)
    _mk2, _sebep3 = d1.marka_kanon_haritasi(fik2)
    dogrula("URETICI: marka_kanon alias'i TASIMAZ (cip/sayfa evreni kanonik kalir) — "
            "iki kolonun kurali AYNI DEGIL",
            _sebep3 is None
            and json.loads(_mk2.get("vaux-1") or "[]") == ["Opel"])

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()
