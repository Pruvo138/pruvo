#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — D1 uzlastiricisinin SILME kolu KARANTINADA mi (K1..K7).

NEDEN VAR (OLCULDU, 11 Agu 2026 — kosum 31532464176, head c8b0451e)
====================================================================
Uzlastirici agaci uzak main ucuna tazeledi, D1'de 37 satiri "FAZLA" sayip SILDI ve
silmeyi geri-okumayla dogruladi:

    hash UYUSMAZ: 0 | D1'de EKSIK: 0 | D1'de FAZLA: 37
    silinen: 37
    GERI-OKUMA DOGRULANDI: 37 satirin ... silinmesi D1'de teyit edildi

O 37 satir COP DEGILDI: eszamanli bir urun partisinin D1'e yazdigi MESRU satirlardi,
partinin git push'u henuz inmemisti. `d1-sync.py --bayatlik` kapisi DOGRU calisti ama
YANLIS SORUYU sordu (agacin git'e gore bayatligi; buradaki hal "D1 git'ten ILERI").

BU TEST NE OLCER — spec: tools/paket-d1-uzlastirici-karantina.md
  K1 id ILK kez FAZLA                        -> SILINMEZ · karantinaya yazilir
  K2 AYNI origin/main SHA'sinda 2. gozlem    -> SILINMEZ (SHA ilerlemedi)
  K3 FARKLI origin/main SHA'sinda 2. gozlem  -> SILINIR
  K4 karantinadaki id AGACTA belirdi         -> SILINMEZ · karantinadan DUSER
  K5 damga YOK / BOZUK                       -> SILME YOK · OLCULEMEDI (fail-closed)
  K6 EKSIK satirlar                          -> karantinadan ETKILENMEZ
  K7 11 Agu vakasinin BIREBIR oynatimi       -> silinen: 0

+ KABLO CAPALARI: karar dogru olsa bile CAGRILMIYORSA olu kalir. Bu yuzden d1-sync.py'nin
  silme kolu (AST ile), uzlastirici-onarim.py'nin bayrak/imza kablosu ve d1-uzlastirici.yml
  / nobet.yml adimlari GERCEK dosyadan olculur ([[nobetci-cagri-satiri-nobetsiz]]).

FIKSTUR SEKLI: K7 gercek kosumun sayisini (37 id) ve gercek head'ini (c8b0451e) tasir;
kisaltilmis sahte sekil DEGIL ([[nobetci-fikstur-sekli]]). Urun id'leri UYDURMADIR
(kisisel/tedarikci verisi YOK) ama SEKLI gercek katalog id'leriyle ayni (kebab-case).

Kullanim:
    python3 tools/uzlastirici-karantina-test.py
    python3 tools/uzlastirici-karantina-test.py --tools /yol/tools   # mutasyon aynasi
Cikis: 0 = tum vakalar gecti · 1 = en az bir vaka KIRMIZI · 2 = OLCULEMEDI (YAML
ayristiricisi yok) — "olcemedim" YESIL DEGILDIR.
"""
import argparse
import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

VARSAYILAN_TOOLS = os.path.dirname(os.path.abspath(__file__))

HATALAR = []
SAYAC = [0]
VAKA_DURUM = {}


def iddia(vaka, ad, kosul, detay=""):
    if not isinstance(detay, str):
        detay = repr(detay)
    SAYAC[0] += 1
    VAKA_DURUM.setdefault(vaka, True)
    if not kosul:
        VAKA_DURUM[vaka] = False
        HATALAR.append("%s: %s%s" % (vaka, ad, ("  -> " + detay) if detay else ""))
    print("  [%s] %s %s%s" % ("PASS" if kosul else "FAIL", vaka, ad,
                              ("  -> " + detay) if detay else ""))
    return kosul


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# FIKSTUR — 11 AGU 2026 KOSUMUNUN SEKLI
# ═══════════════════════════════════════════════════════════════════════════════
# Gercek kosumdaki degerler: head/uzak uc c8b0451e..., FAZLA 37 id, tek gozlem.
SHA_A = "c8b0451e9f2d4a1b7c3e5d6f8a9b0c1d2e3f4a5b"   # 11 Agu kosumunun uzak main ucu
SHA_B = "7d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e"   # BIR SONRAKI kosumun ucu (ilerlemis)

# 37 id — sayisi ve BICIMI gercek vakayla ayni (icerik uydurma; PUBLIC depo).
UCUSTAKI_PARTI = ["ucus-parti-urun-%02d" % i for i in range(1, 38)]


def _damga_yaz_ham(yol, govde):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(govde, f, ensure_ascii=False)


def vaka_kararlari(uk):
    """K1..K5 + K7: SAF hakem (`karar`) uzerinde — disk/ag YOK, saat ENJEKTE."""
    t0 = 1_000_000.0

    # ── K1: ILK GOZLEM -> SILME YOK, karantinaya yazilir ────────────────────
    k = uk.karar(["oksuz-aday-1", "oksuz-aday-2"], {}, SHA_A, t0)
    iddia("K1", "ilk gozlemde HICBIR id silinmez", k["silinecek"] == [], k["silinecek"])
    iddia("K1", "iki id de KARANTINAYA alinir",
          k["acilan"] == ["oksuz-aday-1", "oksuz-aday-2"], k["acilan"])
    iddia("K1", "hukum ACILDI (ONARILAMADI degil — ayri hukum)",
          k["hukum"] == "ACILDI", k["hukum"])
    iddia("K1", "kayitlar O ANKI origin/main SHA'sini tasir",
          all(v["sha"] == SHA_A for v in k["kayitlar"].values()), k["kayitlar"])

    # ── K2: AYNI SHA'da IKINCI gozlem -> SILINMEZ ───────────────────────────
    kayitlar = dict(k["kayitlar"])
    k2 = uk.karar(["oksuz-aday-1", "oksuz-aday-2"], kayitlar, SHA_A, t0 + 900)
    iddia("K2", "AYNI origin/main SHA'sinda 2. gozlem SILMEZ (main ilerlemedi -> "
                "ucustaki parti hala ucusta olabilir)", k2["silinecek"] == [],
          k2["silinecek"])
    iddia("K2", "id'ler karantinada BEKLER (kayit KAYBOLMAZ)",
          sorted(k2["kayitlar"]) == ["oksuz-aday-1", "oksuz-aday-2"], k2["kayitlar"])
    iddia("K2", "hukum BEKLIYOR", k2["hukum"] == "BEKLIYOR", k2["hukum"])
    iddia("K2", "ILK gozlem zamani KORUNUR (her kosumda sifirlanip bayatlik "
                "kolunu olduremez)",
          all(k2["kayitlar"][u]["ts"] == t0 for u in k2["kayitlar"]), k2["kayitlar"])

    # ── K3: FARKLI SHA'da IKINCI gozlem -> SILINIR ──────────────────────────
    k3 = uk.karar(["oksuz-aday-1", "oksuz-aday-2"], kayitlar, SHA_B, t0 + 900)
    iddia("K3", "FARKLI origin/main SHA'sinda 2. gozlem SILER ('ucustaki parti' "
                "aciklamasi CURUDU: o parti inmis olurdu)",
          k3["silinecek"] == ["oksuz-aday-1", "oksuz-aday-2"], k3["silinecek"])
    iddia("K3", "hukum SILINDI", k3["hukum"] == "SILINDI", k3["hukum"])
    iddia("K3", "silinen id karantina kaydindan DUSER (ucuncu kez sayilmaz)",
          k3["kayitlar"] == {}, k3["kayitlar"])

    # ── K4: karantinadaki id AGACTA BELIRDI -> DUSER, SILINMEZ ──────────────
    k4 = uk.karar(["oksuz-aday-2"], kayitlar, SHA_B, t0 + 900)
    iddia("K4", "agacta beliren id (artik FAZLA degil) SILINMEZ",
          "oksuz-aday-1" not in k4["silinecek"], k4["silinecek"])
    iddia("K4", "agacta beliren id KARANTINADAN DUSER",
          k4["dusen"] == ["oksuz-aday-1"] and "oksuz-aday-1" not in k4["kayitlar"],
          (k4["dusen"], sorted(k4["kayitlar"])))

    # ── K5: DAMGA YOK/BOZUK -> FAIL-CLOSED ─────────────────────────────────
    k5 = uk.karar(UCUSTAKI_PARTI, None, SHA_A, t0)
    iddia("K5", "damga OKUNAMAZSA hicbir id silinmez (fail-closed)",
          k5["silinecek"] == [], k5["silinecek"])
    iddia("K5", "hukum OLCULEMEDI ('okuyamadim -> sil' yolu KAPALI)",
          k5["hukum"] == "OLCULEMEDI", k5["hukum"])
    k5b = uk.karar(UCUSTAKI_PARTI, {u: {"sha": SHA_A, "ts": t0} for u in UCUSTAKI_PARTI},
                   "", t0 + 900)
    iddia("K5", "origin/main SHA'si OLCULEMEZSE de silme YOK ('ayni mi farkli mi' "
                "sorusu sorulamaz)",
          k5b["silinecek"] == [] and k5b["hukum"] == "OLCULEMEDI",
          (k5b["silinecek"], k5b["hukum"]))
    k5c = uk.karar(UCUSTAKI_PARTI,
                   {u: {"sha": SHA_A, "ts": t0} for u in UCUSTAKI_PARTI},
                   SHA_B, t0 + uk.TAZELIK_SN + 1)
    iddia("K5", "TAZELIK_SN'den ESKI kayit ikinci gozlem SAYILMAZ -> silme YOK, "
                "id YENIDEN karantinaya alinir (suphede silme)",
          k5c["silinecek"] == [] and len(k5c["acilan"]) == 37,
          (k5c["silinecek"], len(k5c["acilan"])))

    # ── K7: 11 AGU VAKASININ BIREBIR OYNATIMI ──────────────────────────────
    # Gercek kosum: 37 id, TEK gozlem, agac uzak main ucunda (SHA_A). Beklenen: silinen 0.
    silinen_toplam = 0
    for etiket, kayit in (("damga BOS (ilk kosum sonrasi normal hal)", {}),
                          ("damga YOK (bootstrap / artifact inmedi)", None)):
        k7 = uk.karar(UCUSTAKI_PARTI, kayit, SHA_A, t0)
        silinen_toplam += len(k7["silinecek"])
        iddia("K7", "11 Agu (37 id, TEK gozlem) — %s -> silinen: %d"
              % (etiket, len(k7["silinecek"])), k7["silinecek"] == [], k7["silinecek"])
    iddia("K7", "11 Agu vakasinda TOPLAM silinen = 0 (gercek kosumda 37 idi)",
          silinen_toplam == 0, silinen_toplam)
    return silinen_toplam


def vaka_disk(uk):
    """Damganin DISK turu: yaz -> oku -> karar. Bozuk/eksik/yanlis-surum hepsi K5'tir."""
    tmp = tempfile.mkdtemp(prefix="karantina-test-")
    try:
        yol = os.path.join(tmp, uk.DAMGA_DOSYA)
        t0 = 2_000_000.0

        # K1 disk turu: uygula() ILK gozlemi diske TESCIL eder.
        k = uk.uygula(["oksuz-aday-1"], yol, SHA_A, simdi=t0, yaz=lambda *a: None)
        iddia("K1", "uygula(): ilk gozlemde silme YOK ve damga DISKE yazildi",
              k["silinecek"] == [] and os.path.exists(yol), (k["silinecek"], yol))
        kayitlar, _s = uk.damga_oku(yol)
        iddia("K1", "diske yazilan damga geri OKUNABILIR ve id'yi tasir",
              isinstance(kayitlar, dict) and "oksuz-aday-1" in kayitlar, kayitlar)

        # K3 disk turu: farkli SHA -> siler.
        k3 = uk.uygula(["oksuz-aday-1"], yol, SHA_B, simdi=t0 + 900, yaz=lambda *a: None)
        iddia("K3", "uygula(): farkli SHA'da 2. gozlem SILER ve kaydi DUSURUR",
              k3["silinecek"] == ["oksuz-aday-1"], k3["silinecek"])

        # K5 disk turu: dosya YOK / bozuk JSON / yanlis surum / kok dugum liste.
        os.remove(yol)
        kayitlar, sebep = uk.damga_oku(yol)
        iddia("K5", "damga dosyasi YOK -> okunamadi (sebep BASILIR)",
              kayitlar is None and "YOK" in sebep, sebep)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("{bu json degil")
        kayitlar, sebep = uk.damga_oku(yol)
        iddia("K5", "BOZUK JSON -> okunamadi", kayitlar is None, sebep)
        _damga_yaz_ham(yol, {"surum": uk.SURUM + 7, "kayitlar": {}})
        kayitlar, sebep = uk.damga_oku(yol)
        iddia("K5", "YANLIS SURUM -> okunamadi (sema kaymasi sessizce kabul edilmez)",
              kayitlar is None, sebep)
        _damga_yaz_ham(yol, {"surum": uk.SURUM, "kayitlar": ["liste degil sozluk olmali"]})
        kayitlar, sebep = uk.damga_oku(yol)
        iddia("K5", "`kayitlar` sozluk DEGILSE -> okunamadi", kayitlar is None, sebep)
        k5 = uk.uygula(UCUSTAKI_PARTI, yol, SHA_A, simdi=t0, yaz=lambda *a: None)
        iddia("K5", "uygula(): bozuk damga uzerinde 37 id'nin 0'i silinir + hukum "
                    "OLCULEMEDI", k5["silinecek"] == [] and k5["hukum"] == "OLCULEMEDI",
              (k5["silinecek"], k5["hukum"]))
        iddia("K5", "OLCULEMEDI hukmu FAIL-CLOSED IMZASINI basar (uzlastirici-onarim.py "
                    "bu imzayi rc 4'e cevirir)",
              any(uk.OKUNAMADI_IMZASI in s for s in uk.hukum_satirlari(k5, "sebep")),
              uk.hukum_satirlari(k5, "sebep")[:2])

        # `karantinadaki` — --durum teyit kolunun muafiyet kaynagi.
        uk.damga_yaz(yol, {"a": {"sha": SHA_A, "ts": t0},
                           "b": {"sha": SHA_A, "ts": t0 - uk.TAZELIK_SN - 1}}, SHA_A)
        muaf = uk.karantinadaki(yol, simdi=t0)
        iddia("K5", "karantinadaki(): TAZE kayit muaf, BAYAT kayit muaf DEGIL",
              muaf == {"a"}, muaf)
        os.remove(yol)
        iddia("K5", "karantinadaki(): damga yoksa muaf kume BOS (muafiyet KANIT ister)",
              uk.karantinadaki(yol, simdi=t0) == set(), "-")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def vaka_eksik_kolu(tools):
    """K6 — EKSIK/hash kollari karantinadan ETKILENMEZ.

    IKI YONLU: (a) DAVRANIS — gercek `icerik_ekseni()` fiksturu uzerinde EKSIK id'ler
    karantina kaydinda BULUNSA BILE silme koluna GIRMEZ; (b) KABLO (AST) — d1-sync.py'de
    karantina muafiyeti YALNIZ `fazla` degiskenine uygulanir, `eksik`/`uyusmaz`a DEGIL.
    Yalniz (a) olsaydi, muafiyeti eksik koluna da uygulayan bir mutant kacabilirdi."""
    d1 = _modul(os.path.join(tools, "d1-sync.py"), "d1_sync_karantina_testi")
    uk = sys.modules["uzlastirici_karantina_altinda_test"]

    urunler = [{"id": "agacta-var-1", "baslik": "A", "aciklama": "a"},
               {"id": "agacta-var-2", "baslik": "B", "aciklama": "b"}]
    d1_hash = {"agacta-var-1": d1.arama.urun_hash(urunler[0]),
               "d1de-fazla-1": "hash-x"}
    uyusmaz, eksik, fazla = d1.icerik_ekseni(urunler, d1_hash)
    iddia("K6", "fikstur GERCEK icerik_ekseni() ile kuruldu: 1 EKSIK + 1 FAZLA",
          eksik == ["agacta-var-2"] and fazla == ["d1de-fazla-1"], (eksik, fazla))

    # EKSIK id BILEREK karantina kaydina konur — silme koluna girmemeli.
    kayitlar = {"agacta-var-2": {"sha": SHA_A, "ts": 1.0},
                "d1de-fazla-1": {"sha": SHA_A, "ts": 1.0}}
    k = uk.karar(fazla, kayitlar, SHA_B, 2.0)
    iddia("K6", "EKSIK id (D1'de YOK) silme koluna HIC girmez — karar yalniz FAZLA "
                "listesini gorur", "agacta-var-2" not in k["silinecek"], k["silinecek"])
    iddia("K6", "EKSIK id'ler aynen EKLENMEYE devam eder (karar onlara DOKUNMAZ)",
          eksik == ["agacta-var-2"], eksik)

    # (b) KABLO: AST ile — muafiyet hangi degiskene uygulaniyor.
    with open(os.path.join(tools, "d1-sync.py"), encoding="utf-8") as f:
        agac = ast.parse(f.read())
    muaf_hedefleri = set()
    for d in ast.walk(agac):
        if not isinstance(d, ast.Assign):
            continue
        kaynak = ast.dump(d.value)
        if "'muaf'" not in kaynak and '"muaf"' not in kaynak:
            continue
        for t in d.targets:
            if isinstance(t, ast.Name):
                muaf_hedefleri.add(t.id)
    iddia("K6", "d1-sync.py: karantina muafiyeti YALNIZ `fazla` ve `karantinali` "
                "degiskenlerine uygulanir (`eksik`/`uyusmaz` DOKUNULMAZ)",
          muaf_hedefleri and muaf_hedefleri <= {"fazla", "karantinali"}, muaf_hedefleri)


def kablo_capalari(tools, kok):
    """CAGRI SATIRI NOBETSIZ KALMASIN — karar dogru olsa bile kablo kopuksa OLU kalir."""
    d1_yol = os.path.join(tools, "d1-sync.py")
    with open(d1_yol, encoding="utf-8") as f:
        d1_metin = f.read()
    agac = ast.parse(d1_metin)

    uygula_cagrisi = False
    silinen_atamasi = False
    olculemedi_cikisi = False
    for d in ast.walk(agac):
        if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and d.func.attr == "uygula"
                and isinstance(d.func.value, ast.Name)
                and d.func.value.id == "uzlastirici_karantina"):
            uygula_cagrisi = True
        if isinstance(d, ast.Assign):
            hedefler = {t.id for t in d.targets if isinstance(t, ast.Name)}
            if "silinen" in hedefler and "'silinecek'" in ast.dump(d.value):
                silinen_atamasi = True
        if isinstance(d, ast.If) and "OKUNAMADI_IMZASI" in ast.dump(d):
            olculemedi_cikisi = True
    iddia("KABLO", "d1-sync.py silme kolunda uzlastirici_karantina.uygula() CAGRILIR",
          uygula_cagrisi)
    iddia("KABLO", "`silinen` listesi karar sonucundaki `silinecek` ile DEGISTIRILIR "
                   "(karar hesaplanip ATILIRSA silme aynen surerdi)", silinen_atamasi)
    iddia("KABLO", "OLCULEMEDI hali SIFIR-DISI cikisa baglidir ('olcemedim' YESIL degil)",
          olculemedi_cikisi)

    with open(os.path.join(tools, "uzlastirici-onarim.py"), encoding="utf-8") as f:
        onarim = f.read()
    iddia("KABLO", "uzlastirici-onarim.py d1-sync'i `--karantina-damgasi` ile cagirir",
          '"--karantina-damgasi", KARANTINA_DAMGASI' in onarim)
    iddia("KABLO", "uzlastirici-onarim.py fail-closed imzayi rc 4'e cevirir "
                   "(YENIDEN DENEMEZ: damgayi tekrar okumak onu VAR ETMEZ)",
          "KARANTINA_IMZASI in cikti" in onarim and "return 4, deneme" in onarim)

    # ── IS AKISI (GERCEK YAML AYRISTIRICISI — metin taklidi YOK) ───────────
    nabiz = _modul(os.path.join(tools, "cron-nabiz-kapisi.py"), "cnk_karantina_testi")
    if nabiz.yaml_ayristirici_adi() is None:
        print("\n🔴 OLCULEMEDI: GERCEK YAML ayristiricisi YOK (ne PyYAML ne ruby/psych).")
        sys.exit(2)
    uzl_yol = os.path.join(kok, ".github", "workflows", "d1-uzlastirici.yml")
    nob_yol = os.path.join(kok, ".github", "workflows", "nobet.yml")
    with open(uzl_yol, encoding="utf-8") as f:
        uzl = nabiz.yaml_belge(f.read())
    with open(nob_yol, encoding="utf-8") as f:
        nob = nabiz.yaml_belge(f.read())

    adimlar = []
    for _ad, job in (uzl.get("jobs") or {}).items():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            adimlar.extend(a for a in job["steps"] if isinstance(a, dict))
    komutlar = [str(a.get("run") or "") for a in adimlar]

    # 🔴 IDDIA SAYISI KOSULSUZ SABITTIR: `if bulundu:` ile korunan iddialar, adimi
    # SILEN bir mutantta HIC KOSMAZ ve "sayi dusmesi" cokme kirmizisiyla karisirdi
    # ([[mutasyon-kaniti-yeniden-uretilebilir]]). Bulunamayan adim BOS SOZLUKtur.
    indir = [a for a in adimlar if "--indir" in str(a.get("run") or "")]
    ind = indir[0] if len(indir) == 1 else {}
    iddia("KABLO", "d1-uzlastirici.yml onceki kosumun karantina damgasini INDIRIR",
          len(indir) == 1 and "uzlastirici_karantina.py" in str(ind.get("run") or ""),
          [str(a.get("name")) for a in indir])
    iddia("KABLO", "indirme adimi tazeleme TEYIDINE kosullu (bayat agacta damga "
                   "okumak yanlis eksende hukum uretirdi)",
          "steps.bayatlik.outputs.uc" in str(ind.get("if") or ""), str(ind.get("if")))

    yukleme = None
    for a in adimlar:
        if str(a.get("uses") or "").startswith("actions/upload-artifact"):
            ile = a.get("with") if isinstance(a.get("with"), dict) else {}
            if str(ile.get("name") or "") == "d1-karantina-damgasi":
                yukleme = ile
    yuk = yukleme or {}
    iddia("KABLO", "karantina damgasi `d1-karantina-damgasi` adiyla YUKLENIR (yoksa "
                   "her kosum 'ilk gozlem' sanilir ve silme kolu ASLA calismaz)",
          yukleme is not None, yukleme)
    iddia("KABLO", "yuklenen `path` damga dosyasiyla AYNI",
          str(yuk.get("path") or "").strip() == "karantina-damgasi.json",
          yuk.get("path"))
    iddia("KABLO", "`if-no-files-found: error` — damga dogmazsa adim KIRMIZI "
                   "(sessiz hafiza kaybi yok)",
          str(yuk.get("if-no-files-found") or "").lower() == "error",
          yuk.get("if-no-files-found"))

    teyit = [k for k in komutlar if "--durum" in k and "--karantina-damgasi" in k]
    iddia("KABLO", "TEYIT adimi `--durum --karantina-damgasi` ile kosar (karantinaya "
                   "alinan id 'onarilamadi' sayilmaz)", len(teyit) == 1, len(teyit))
    olcum = [a for a in adimlar if str(a.get("id") or "") == "olcum"]
    olc = olcum[0] if len(olcum) == 1 else {}
    iddia("KABLO", "ONARIM ONCESI olcum adimi bayraksiz kosar -> sapma TAM olculur ve "
                   "`d1-sapma-damgasi` alarm kanali AYNEN kirmizi yakar (susturma YOK)",
          len(olcum) == 1 and "--karantina-damgasi" not in str(olc.get("run") or ""),
          str(olc.get("run") or "")[:80])
    iddia("KABLO", "sapma YOK kolunda damga BOSALTILIR (bayat kayit ilerideki bir "
                   "kosumda 'ikinci gozlem' gibi gorunemesin)",
          any("--temizle karantina-damgasi.json" in k for k in komutlar))
    iddia("KABLO", "sapma VAR kolunda damga dosyasi YOKSA tescil edilir ama VAR OLAN "
                   "damga EZILMEZ (`--temizle-yoksa`) — ezilseydi ikinci gozlem "
                   "hafizasi her kosumda sifirlanir, silme kolu SESSIZCE olurdu",
          any("--temizle-yoksa karantina-damgasi.json" in k for k in komutlar))

    izinler = uzl.get("permissions") if isinstance(uzl.get("permissions"), dict) else {}
    iddia("KABLO", "d1-uzlastirici.yml `actions: read` ister (artifact listelenip "
                   "indirilebilsin)", str(izinler.get("actions") or "") == "read", izinler)
    kadans = None
    for _ad, job in (nob.get("jobs") or {}).items():
        if isinstance(job, dict) and "d1-uzlastirici.yml" in str(job.get("uses") or ""):
            kadans = job
    iddia("KABLO", "nobet.yml kadans kolu da `actions: read` gecer (cagrilan is akisinin "
                   "jetonu CAGIRAN job'un izinleriyle TAVANLANIR)",
          isinstance(kadans, dict)
          and str((kadans.get("permissions") or {}).get("actions") or "") == "read",
          (kadans or {}).get("permissions"))


def main():
    ap = argparse.ArgumentParser(description="Uzlastirici silme karantinasi kabul testi")
    ap.add_argument("--tools", default=VARSAYILAN_TOOLS,
                    help="olculecek tools dizini (mutasyon aynasi icin)")
    a = ap.parse_args()
    tools = os.path.abspath(a.tools)
    kok = os.path.dirname(tools)
    sys.path.insert(0, tools)

    print("UZLASTIRICI SILME KARANTINASI — KABUL TESTI (K1..K7)")
    print("olculen tools: %s\n" % tools)
    uk = _modul(os.path.join(tools, "uzlastirici_karantina.py"),
                "uzlastirici_karantina_altinda_test")

    silinen_k7 = vaka_kararlari(uk)
    vaka_disk(uk)
    vaka_eksik_kolu(tools)
    kablo_capalari(tools, kok)

    for vaka in ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "KABLO"):
        VAKA_DURUM.setdefault(vaka, False)
        if not VAKA_DURUM[vaka]:
            HATALAR.append("%s vakasi HIC KOSMADI (harness bayat)" % vaka)
    gecen = SAYAC[0] - len(HATALAR)
    print("\nK7 = %s (11 Agu vakasinda silinen: %d)"
          % ("GECTI" if VAKA_DURUM.get("K7") else "DUSTU", silinen_k7))
    print("%d iddia kosturuldu, %d KIRMIZI." % (SAYAC[0], len(HATALAR)))
    print("KARANTINA_TESTI=%d:%d/%d" % (1 if HATALAR else 0, gecen, SAYAC[0]))
    if HATALAR:
        print("🔴 KARANTINA KABUL TESTI KIRMIZI:")
        for h in HATALAR:
            print("   - %s" % h)
        return 1
    print("✅ K1..K7 + kablo capalari GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
