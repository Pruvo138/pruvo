#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — d1-sync KATALOG KAYNAGI: `--head` / `--kaynak` gercekten HEAD'den okuyor mu,
bayraksiz davranis BIREBIR ayni mi?

  python3 tools/d1-kaynak-test.py

SORUN (olculen tuzak, 5 Agu 2026 — AYNI GUN IKI KEZ):
`d1-sync.py` katalogu DAIMA calisma agacindaki `urunler.json`'dan okur. Agacta baska bir
oturumun COMMIT'LENMEMIS urunleri varsa senkron ONLARI CANLIYA YAZAR ve hicbir sey kirmizi
yanmaz: bayatlik kapisi COMMIT GRAFIGINI olcer ("HEAD uzak ucu biliyor mu"), calisma
agacinin o commit'ten SAPIP SAPMADIGINI OLCMEZ. O gun `model_kanon` geriye doldurmasi tam
bu yuzden ertelendi (agacta 105 commit'lenmemis urun vardi).

BU TESTIN OLCTUGU IKI SEY:
  1. 🔴 AYIRT EDICI: GERCEK bir git fikstur deposunda, agacta commit'lenmemis bir urun
     varken `--head` kaynagi onu ICERMEZ, varsayilan (agac) kaynagi ICERIR. Fikstur bu
     farki TASIMASAYDI iki yol da ayni sayiyi doner ve eksen SESSIZCE olculmez olurdu
     ([[fikstur-degeri-mutasyon-koru]]).
  2. BAYRAKSIZ DAVRANIS DEGISMEDI: bayrak verilmeyince modul sabitine DOKUNULMAZ ve
     cikti YENI BIR SATIR BASMAZ (kancalar bugunku davranisa bagli).
  3. [D] `d1-kaynak-sync.py --durum` YETIM SINIFLAMASI (21 Eki): EKSIK link urunu
     katalogda yoksa SILINMIS (kirmizi yakmaz), varsa GERCEK_EKSIK (SAPMA), katalog
     okunamazsa OLCULEMEDI. Olcum oncesi 463 eksigin hepsi SAPMA'ydi; gercek eksik
     gurultunun icinde gorunmuyordu.

CANLI D1'e / wrangler'a / AGA DOKUNMAZ. Mutasyon surucusu: tools/d1-kaynak-mutasyon.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from git_ortami import git_ortami, sentetik_git  # noqa: E402

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


d1 = yukle_modul("d1_sync_kaynak", "d1-sync.py")


def _urun(uid, baslik):
    return {"id": uid, "baslik": baslik, "kategori": "Oyun/Hobi", "marka": [],
            "fiyat": "100 TL", "gorseller": ["https://media.example/%s-1.jpg" % uid],
            "aciklama": "aciklama %s" % uid}


def _git(kok, *args):
    return sentetik_git(kok, *args, capture_output=True, text=True,
                         kimlik_ad="t", kimlik_eposta="t@t")


def fikstur_kur(tmp):
    """GERCEK git deposu: 2 urun COMMIT'LI, 1 urun COMMIT'LENMEMIS (agacta).
    🔴 Fikstur bu farki TASIMAK ZORUNDA — tasimasaydi iki kaynak da ayni sonucu verir
    ve testin asil ekseni korelirdi."""
    kok = os.path.join(tmp, "depo")
    os.makedirs(kok)
    _git(kok, "init", "-q")
    yol = os.path.join(kok, "urunler.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump([_urun("commitli-2", "B"), _urun("commitli-1", "A")], f,
                  ensure_ascii=False)
    _git(kok, "add", "urunler.json")
    _git(kok, "commit", "-q", "-m", "iki urun")
    # AGACA commit'LENMEMIS ucuncu urun + commit'li bir urunun ICERIGI de degistirilir
    # (iki ayri sapma sinifi: YENI id ve DEGISEN icerik).
    with open(yol, "w", encoding="utf-8") as f:
        json.dump([_urun("commitlenmemis-3", "C"), _urun("commitli-2", "B DEGISTI"),
                   _urun("commitli-1", "A")], f, ensure_ascii=False)
    return kok, yol


# ══ A) AYIRT EDICI EKSEN — commit'lenmemis urun --head kaynagina GIRMEZ ══════════
print("\n[A] AYIRT EDICI — gercek git fiksturunde commit'lenmemis urun")
tmp = tempfile.mkdtemp(prefix="d1-kaynak-test-")
kok_f, yol_f = fikstur_kur(tmp)
_gercek_kok, _gercek_urunler = d1.KOK, d1.URUNLER
try:
    d1.KOK, d1.URUNLER = kok_f, yol_f

    agac = json.load(open(yol_f, encoding="utf-8"))
    dogrula("A1 FIKSTUR AYIRT EDICI: agacta 3 urun, commit'te 2 (fark TASINIYOR)",
            len(agac) == 3 and "commitlenmemis-3" in [u["id"] for u in agac])

    # 🔴 OLCUM `kaynak_coz` UZERINDEN yapilir, `head_katalogu` DOGRUDAN cagrilmaz:
    # main'in kullandigi yol budur. Dogrudan cagrilsaydi, `kaynak_coz`'un --head dalini
    # calisma agacina ceviren bir mutant (bayragin SESSIZ ETKISIZLIGI — tam da kapatilmak
    # istenen hata) bu iddialarin HICBIRINDE gorunmezdi; olculdu ve duzeltildi.
    yol_h, beyan_h, gecici_h = d1.kaynak_coz(None, True)
    sha = _git(kok_f, "rev-parse", "HEAD").stdout.strip()
    dogrula("A2a kaynak_coz(--head) GECICI bir dosya doner (agac dosyasini DEGIL)",
            gecici_h is True and yol_h != yol_f, "%s / %s" % (gecici_h, yol_h))
    head = json.load(open(yol_h, encoding="utf-8"))
    head_idler = [u["id"] for u in head]
    dogrula("A2 🔴 --head kaynagi COMMIT'LENMEMIS urunu ICERMEZ (2 urun, %s)"
            % head_idler, len(head) == 2 and "commitlenmemis-3" not in head_idler,
            str(head_idler))
    dogrula("A3 KONTROL (ters yon): varsayilan kaynak (agac) onu ICERIR — iki yol "
            "GERCEKTEN farkli sonuc veriyor",
            "commitlenmemis-3" in [u["id"] for u in agac])
    dogrula("A4 --head icerigi `git show HEAD:urunler.json` ile BIREBIR",
            open(yol_h, encoding="utf-8").read()
            == _git(kok_f, "show", "HEAD:urunler.json").stdout)
    dogrula("A5 beyan HEAD sha'sini tasir (operator hangi commit'ten kostugunu GORUR): %s"
            % beyan_h, sha[:12] in beyan_h and "HEAD" in beyan_h, beyan_h)

    # SAPMA OLCUMU = operatorun "commit'lenmemis veri yazilmadi" KANITI.
    yalniz_k, yalniz_a, hash_farki = d1.kaynak_sapmasi(yol_h)
    dogrula("A6 kaynak_sapmasi IKI sapma sinifini de sayar: yalniz agacta %s · icerigi "
            "farkli %s" % (yalniz_a, hash_farki),
            yalniz_a == ["commitlenmemis-3"] and hash_farki == ["commitli-2"]
            and yalniz_k == [],
            "k=%s a=%s h=%s" % (yalniz_k, yalniz_a, hash_farki))
    # 🔴 YALNIZ GECICI dosya silinir: bir mutant yol_h'yi AGAC dosyasina cevirebilir ve
    # kosulsuz unlink fiksturu yok ederdi -> sonraki iddialar cokerdi. Cokme kirmiziyla
    # karisir, mutant "oldurulmus" sayilirdi ([[mutasyon-kaniti-yeniden-uretilebilir]]).
    if gecici_h and yol_h != yol_f:
        os.unlink(yol_h)

    # ══ B) FAIL-CLOSED — sessizce CALISMA AGACINA DUSMEK YOK ════════════════════
    print("\n[B] FAIL-CLOSED — secilen kaynak okunamazsa arac DURUR")
    for ad, cagri in (
        ("B1 --kaynak + --head BIRLIKTE reddedilir (belirsizlik)",
         lambda: d1.kaynak_coz("/yok/olmayan.json", True)),
        ("B2 --kaynak dosyasi YOKSA sys.exit (agaca DUSMEZ)",
         lambda: d1.kaynak_coz(os.path.join(tmp, "__yok__.json"), False)),
    ):
        try:
            cagri()
            dogrula(ad, False, "sys.exit ATILMADI")
        except SystemExit:
            dogrula(ad, True)
    bozuk = os.path.join(tmp, "bozuk.json")
    with open(bozuk, "w", encoding="utf-8") as f:
        f.write('{"dizi": "degil"}')
    try:
        d1.kaynak_dogrula(bozuk)
        dogrula("B3 kaynak DIZI degilse sys.exit (bicimsiz kaynakla senkron KOSMAZ)",
                False, "sys.exit ATILMADI")
    except SystemExit:
        dogrula("B3 kaynak DIZI degilse sys.exit (bicimsiz kaynakla senkron KOSMAZ)", True)
    dogrula("B4 gecerli --kaynak KABUL edilir ve benzersiz id sayar",
            d1.kaynak_dogrula(yol_f) == 3, str(d1.kaynak_dogrula(yol_f)))
finally:
    d1.KOK, d1.URUNLER = _gercek_kok, _gercek_urunler

# ══ C) BAYRAKSIZ DAVRANIS BIREBIR AYNI ═══════════════════════════════════════════
print("\n[C] BAYRAKSIZ DAVRANIS — kancalar buna bagli, DEGISMEMELI")
yol0, beyan0, gecici0 = d1.kaynak_coz(None, False)
dogrula("C1 bayraksiz -> yol None (modul sabitine DOKUNULMAZ)",
        yol0 is None and gecici0 is False, "%s / %s" % (yol0, gecici0))
dogrula("C2 modul sabiti hala calisma agacini gosteriyor",
        d1.URUNLER == os.path.join(KOK, "urunler.json"), d1.URUNLER)
kaynak = open(os.path.join(TOOLS, "d1-sync.py"), encoding="utf-8").read()
dogrula("C3 main'de kaynak blogu KOSULLU (`if _kaynak_yolu:`) — bayraksiz kosumda hic "
        "calismaz, dolayisiyla YENI SATIR da basmaz", "if _kaynak_yolu:" in kaynak)
dogrula("C4 atama YALNIZ o kosulun ICINDE (kosulsuz atama olsaydi varsayilan da kayardi)",
        kaynak.count('globals()["URUNLER"] = _kaynak_yolu') == 1
        and kaynak.index("if _kaynak_yolu:")
        < kaynak.index('globals()["URUNLER"] = _kaynak_yolu'))

# UCTAN UCA: alt surecte bayraksiz kosum "KATALOG KAYNAGI" satirini BASMAZ, bayrakli
# BASAR. Iki yon de olculur (tek yon olculseydi "hic basmiyor" da gecerdi).
r0 = subprocess.run([sys.executable, os.path.join(TOOLS, "d1-sync.py"), "--kendini-test"],
                    capture_output=True, text=True, cwd=KOK, env=git_ortami())
r1 = subprocess.run([sys.executable, os.path.join(TOOLS, "d1-sync.py"), "--kendini-test",
                     "--head"], capture_output=True, text=True, cwd=KOK,
                    env=git_ortami())
dogrula("C5 bayraksiz `--kendini-test`: rc=0 ve ciktida 'KATALOG KAYNAGI' YOK",
        r0.returncode == 0 and "KATALOG KAYNAGI" not in r0.stdout,
        "rc=%d" % r0.returncode)
dogrula("C6 KONTROL (ters yon): `--head` ile AYNI kosum rc=0 ve 'KATALOG KAYNAGI' BASAR "
        "(nobetci olu degil)",
        r1.returncode == 0 and "KATALOG KAYNAGI" in r1.stdout, "rc=%d" % r1.returncode)
dogrula("C7 bayrak `--kendini-test` sonucunu DEGISTIRMEZ (iddia sayilari birebir)",
        [s for s in r0.stdout.splitlines() if s.startswith("SONUC")]
        == [s for s in r1.stdout.splitlines() if s.startswith("SONUC")],
        "%s vs %s" % ([s for s in r0.stdout.splitlines() if s.startswith("SONUC")],
                      [s for s in r1.stdout.splitlines() if s.startswith("SONUC")]))

import shutil                                                       # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

# ══ D) YETIM SINIFLAMASI — d1-kaynak-sync.py --durum EKSIK kirilimi ════════════════
# EKSIK link urunu katalogda YOKSA SILINMIS (kirmizi yakmaz), VARSA GERCEK_EKSIK (SAPMA).
# Gizli kayit, katalog ve D1 sahte: gecici dosyalar + ortak gercek wrangler zarfi. AGA CIKMAZ.
print("\n[D] YETIM SINIFLAMASI — SILINMIS / GERCEK_EKSIK / OLCULEMEDI")
import contextlib                                                   # noqa: E402
import io                                                           # noqa: E402
import d1_zarf_fikstur                                              # noqa: E402

ks = yukle_modul("d1_kaynak_sync_yetim", "d1-kaynak-sync.py")
tmp_d = tempfile.mkdtemp(prefix="d1-kaynak-yetim-")


def _yaz(ad, veri):
    yol = os.path.join(tmp_d, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(veri if isinstance(veri, str) else json.dumps(veri))
    return yol


def _durum(yerel_idler, d1_idler, katalog):
    """durum()'u sahte gizli kayit + katalog + D1 zarfiyla kos -> (rc, cikti)."""
    ks.KAYNAKLAR = _yaz("kaynaklar.json",
                        {i: {"link": "https://example.com/%s" % i} for i in yerel_idler})
    ks.URUNLER = _yaz("urunler.json", katalog)
    satirlar = [{"id": i, "link": "https://example.com/%s" % i} for i in d1_idler]
    ks.ds = type("DS", (), {"sorgu": staticmethod(
        lambda sql: d1_zarf_fikstur.zarf(satirlar) if "FROM urun_kaynak" in sql
        else d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}]))})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ks.durum()
    return rc, buf.getvalue()


def _katalog(*idler):
    return [{"id": i, "baslik": i} for i in idler]


_gercek_ds = ks.ds
try:
    dogrula("D1 katalog_idleri gecerli katalogdan id kumesini okur",
            ks.katalog_idleri(_yaz("k.json", _katalog("a", "b"))) == {"a", "b"})
    bozuklar = {"dizi-degil": {"id": "a"}, "json-degil": "{bozuk", "bos-dizi": [],
                "idsiz-kayit": [{"id": "a"}, {"baslik": "id yok"}],
                "dosya-yok": None}
    sonuc_b = {ad: ks.katalog_idleri(_yaz("b-%s.json" % ad, v) if v is not None
                                     else os.path.join(tmp_d, "__yok__.json"))
               for ad, v in bozuklar.items()}
    dogrula("D2 bozuk katalog (dizi degil / json degil / bos / id'siz kayit / dosya yok) "
            "-> None (OLCULEMEDI, fail-closed)",
            all(v is None for v in sonuc_b.values()), str(sonuc_b))
    s3 = ks.yetim_sinifla(["silinmis-1", "var-1"], {"var-1", "baska"})
    dogrula("D3 silinmis id -> SILINMIS, katalogda var-ama-D1'de-yok -> GERCEK_EKSIK",
            s3 == {"SILINMIS": ["silinmis-1"], "GERCEK_EKSIK": ["var-1"]}, str(s3))

    rc4, c4 = _durum(["a", "b", "c"], ["a"], _katalog("a", "b"))
    dogrula("D4 durum: 1 silinmis + 1 gercek eksik -> 'YETIM SILINMIS=1 GERCEK_EKSIK=1 "
            "TOPLAM=2', HUKUM=SAPMA rc=1",
            "YETIM SILINMIS=1 GERCEK_EKSIK=1 TOPLAM=2" in c4 and "HUKUM=SAPMA" in c4
            and rc4 == 1, "rc=%d %r" % (rc4, c4[-160:]))
    rc5, c5 = _durum(["a", "c"], ["a"], _katalog("a", "b"))
    dogrula("D5 🔴 yalniz SILINMIS kaldiysa kirmizi YAKMAZ: SILINMIS=1 GERCEK_EKSIK=0, "
            "HUKUM=SENKRON rc=0",
            "YETIM SILINMIS=1 GERCEK_EKSIK=0 TOPLAM=1" in c5 and "HUKUM=SENKRON" in c5
            and rc5 == 0, "rc=%d %r" % (rc5, c5[-160:]))
    rc6, c6 = _durum(["a", "c"], ["a"], "{bozuk")
    dogrula("D6 katalog okunamazsa YETIM OLCULEMEDI + HUKUM=OLCULEMEDI rc=1 (SENKRON "
            "denmez)",
            "YETIM OLCULEMEDI" in c6 and "HUKUM=OLCULEMEDI" in c6 and rc6 == 1
            and "HUKUM=SENKRON" not in c6, "rc=%d %r" % (rc6, c6[-160:]))
    eksik4 = [s for s in c4.splitlines() if s.startswith("EKSIK=")]
    dogrula("D7 sinif toplami = EKSIK satiri (TOPLAM=2 ve EKSIK=2)",
            eksik4 == ["EKSIK=2"] and "TOPLAM=2" in c4, str(eksik4))
    rc8, c8 = _durum(["a"], ["a", "z"], _katalog("a"))
    dogrula("D8 FAZLA>0 iken GERCEK_EKSIK=0 olsa da HUKUM=SAPMA rc=1 (fazla satir "
            "susturulmaz)",
            "FAZLA=1" in c8 and "HUKUM=SAPMA" in c8 and rc8 == 1,
            "rc=%d %r" % (rc8, c8[-160:]))
    rc10, c10 = _durum(["a", "b", "c"], ["a", "c"], _katalog("a", "b", "d"))
    dogrula("D10 UZLASMA: katalog = TAM + GERCEK_EKSIK + LINKSIZ, D1 = KATALOGDA + "
            "KATALOG_DISI",
            "UZLASMA KATALOG=3 TAM=1 GERCEK_EKSIK=1 LINKSIZ=1" in c10
            and "UZLASMA D1_SATIR=2 KATALOGDA=1 KATALOG_DISI=1" in c10,
            "rc=%d %r" % (rc10, c10[-200:]))
    dogrula("D9 GIZLILIK: durum ciktisinda link yok (yalniz SAYI)",
            all("://" not in c for c in (c4, c5, c6, c8, c10)))
finally:
    ks.ds = _gercek_ds
    shutil.rmtree(tmp_d, ignore_errors=True)

print("\nNE OLCULMEDI (beyan):")
print("  1. CANLI SENKRON YOLU: --kaynak/--head ile fiilen D1'e yazan kosum burada")
print("     KOSULMAZ (test aga/D1'e dokunmaz). Bayragin senkron dalindaki etkisi tek")
print("     bir noktadan gecer (main'deki `globals()[\"URUNLER\"]` atamasi) ve o nokta")
print("     C3/C4'te yapisal olarak olculur.")
print("  2. Bayraksiz kosumun TAM BAYT ciktisi, degisiklik ONCESI surumle burada")
print("     karsilastirilmaz (HEAD artik bayragi iceriyor -> kiyas totolojik olurdu).")
print("     O kiyas bir kez ELLE olculdu, sayisi muhendis raporunda.")

print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
sys.exit(1 if kalan[0] else 0)
