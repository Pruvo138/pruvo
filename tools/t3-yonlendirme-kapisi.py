#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/t3-yonlendirme-kapisi.py — PAKET T3: SAHTE KIRMIZI YONLENDIRME KAPISI.

Mimar hukumu (18 Agu 2026, KraL): `tools/paket-t3-sahte-kirmizi-yonlendirme.md`.

EV ekseni KAT ekseninden AYRIDIR: KAT = is hangi motorun yaptigi, EV = kalemin
kimin defterine (posta kutusuna) dustugu. nobet-kapi.py YALNIZ KAT ekseninde
dagitiyor; bu kapi EV eksenini HARITADAN (`tools/sahiplik-haritasi.tsv`) okur.

4 kol — her birinin MUTANT tarafindan hedef kolu kanitlanmistir:
  T3-YON          : haritadan EV cozumle, hedef evin posta kutusuna yaz,
                    KRAI'daki satir silinmez; `DEVREDILDI: <EV> <damga>` ile
                    isaretlenir.
  T3-SAHIPSIZ     : mekanizma haritada YOK ise BILINMIYOR; kalem MIMAR'da
                    KALIR + SAHIPSIZ sayaci artar (sessiz varsayilan YOK).
                    Mesaj `T3-SAHIPSIZ ` onekiyle baslar.
  T3-OLCULEMEDI   : hedef kutuya yazma BASARISIZ ise tatbikat KIRMIZI +
                    OLCULEMEDI (fail-closed; "teslim edildi" DEGIL).
                    Mesaj `T3-OLCULEMEDI ` onekiyle baslar.
  T3-IZ           : DEVREDILDI izi yazma kanali oldurulurse (KraL'in posta
                    kutusu yazilamaz) YAZILDI True KALMAZ + HATA.
                    Mesaj `T3-IZ ` onekiyle baslar.
  (kod yolu — mutanti yok) T3-EV-GECERSIZ: ev_adresi() gecersiz EV donusu
                    icin AYRI hata sinifi; SAHIPSIZ ASLA True set edilmez;
                    mesaj `T3-EV-GECERSIZ ` onekiyle baslar. Bu sayede
                    T3-SAHIPSIZ govdesi oldurulunce M2, T3-EV-GECERSIZ
                    mesajini gormez (kol ayrimi).

Mutasyon bataryasi kurali (EK, 18 Agu 2026): haritanin evreni -test/-mutasyon/-prob
dislar; bu yuzden `X-mutasyon.py` icin EV, olctugu kapinin EV'idir
(`X-kapisi.py` ya da `X.py`). Eslesme yoksa BILINMIYOR.

Icerikten EV turetimi (EK, 19 Agu 2026 — PAKET T3b): ad-ekseni ve mutant-turev
adimi ile cozulemeyen bir mekanizma icin dosyanin metni okunur; icinden toplanan
tools/ referanslarinin haritadaki EV'leri arasinda TAM OLARAK BIR ayirt edici
EV varsa o doner. SIFIR → BILINMIYOR (sahipsiz kalir); BIRDEN COK → BILINMIYOR
+ CAKISMA sayaci artar. Sessiz secim / varsayilan EV YASAK. Okuma IO/encoding
hatasinda BILINMIYOR + OKUNAMADI sayaci artar; sessiz 0 yasak.

Isletim modlari:
  default (analiz)   : gercek harita uzerinde EV dagilimini basar; YAZMAZ.
  --kendini-test     : 4 mutant + izolasyon (tempfile.mkdtemp); gercek posta
                       kutularina DOKUNMAZ.
  --tatbikat         : sentetik sahte kirmizi uretir + gercek posta kutusuna
                       yazar; AYNI kosumda siler ve TEMIZ=EVET kanitlar.

KABUL (calistirilabilir):
  python3 tools/t3-yonlendirme-kapisi.py --kendini-test
    -> rc=0, MUTANT=4/4, T3-YON, T3-SAHIPSIZ, T3-OLCULEMEDI, T3-IZ gecti,
       SAHIPSIZ ayri basildi, TEMIZ=EVET kanitlandi.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - harita TSV'yi kendi-test icin gecici yedek + geri koyma ile izole eder.
  - --kendini-test gercek posta kutusunu ASLA hedeflemez; kok parametreyle
    verilir ve tempfile.mkdtemp() altinda kosar.
  - --tatbikat gercek kutuya yazarsa AYNI koşumda siler, TEMIZ=EVET kanitlar;
    kanitlayamazsa TEMIZ=OLCULEMEDI + rc!=0.
  - DEVREDILDI izi: EV != KraL ise KraL'in posta kutusuna TEK satir yazilir.
    Yazma BASARISIZSA fail-closed: YAZILDI True KALMAZ + HATA OLCULEMEDI.
"""
import argparse
import datetime
import json
import os
import shutil
import stat
import sys
import tempfile

# ---- sabitler -----------------------------------------------------------------
HARITA_RELATIF = "tools/sahiplik-haritasi.tsv"

# EV -> kutu yolu koku (proje bazinda). KraL kendi kokundedir (ek yok).
# Spec: ~/.claude/projects/-Users-okan-dev-pruvo-<hasat|pazarlama|bot|jenerator>/memory/mimar-posta-kutusu.md
EV_DIZIN = {
    "KraL":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
    "MaCiT":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-hasat",
    "ArTisT":  "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-pazarlama",
    "HocA":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-bot",
    "TeKiN":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-jenerator",
    "BaBa":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",  # BaBa KraL'da oturur (yoksa yok say)
    "ORTAK":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
}

POSTA_DOSYA = "memory/mimar-posta-kutusu.md"

# Bilinen EV degerleri — harita icin.
EV_BILINEN = {"KraL", "MaCiT", "TeKiN", "ArTisT", "HocA", "BaBa", "ORTAK"}
EV_KABUL = EV_BILINEN | {"BILINMIYOR"}

# Hedef kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir.
# Kol ATIFI mesajin BASINDA gecer; mutant dogrulamasi `startswith(kol + " ")`
# ile yalnizca kendi kolunun imzasini dogrular. Bu sayede bir kol oldurulunce
# diger kolun mesaji onun yerine gecse bile mutant YASAMAZ (kol ayrimi).
T3_YON_JETON          = "T3-YON"
T3_SAHIPSIZ_JETON     = "T3-SAHIPSIZ"
T3_OLCULEMEDI_JETON   = "T3-OLCULEMEDI"
T3_IZ_JETON           = "T3-IZ"
T3_EV_GECERSIZ_JETON  = "T3-EV-GECERSIZ"   # ev_adresi() gecersiz EV donusu

# Mutant adlari + hedef kol eslestirmesi.
MUTANT_HEDEF = {
    "M1": T3_YON_JETON,
    "M2": T3_SAHIPSIZ_JETON,
    "M3": T3_OLCULEMEDI_JETON,
    "M4": T3_IZ_JETON,
}

# ------------------------------------------------------------------------------
# HARITA
# ------------------------------------------------------------------------------
def _repo_kok():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def haritayi_oku(repo_kok, harita_yolu):
    """TSV -> [{MEKANIZMA, YOL, EV, SERIT, KABUL_KOMUTU, SATIR_NO}, ...]"""
    tam = harita_yolu if os.path.isabs(harita_yolu) else os.path.join(repo_kok, harita_yolu)
    if not os.path.isfile(tam):
        return [], []
    with open(tam, encoding="utf-8") as f:
        satirlar = f.readlines()
    satirlar = [s.rstrip("\n") for s in satirlar]
    veri = []
    hatalar = []
    baslik_gecti = False
    for i, s in enumerate(satirlar, 1):
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        kolonlar = s.split("\t")
        if not baslik_gecti and kolonlar[0].strip() == "MEKANIZMA":
            baslik_gecti = True
            continue
        baslik_gecti = True
        if len(kolonlar) < 5:
            hatalar.append("satir %d: 5 kolon bekleniyor, %d bulundu: %r"
                           % (i, len(kolonlar), s[:80]))
            continue
        mekanizma, yol, ev, serit, kabul_komutu = [k.strip() for k in kolonlar[:5]]
        if not mekanizma or not yol:
            hatalar.append("satir %d: MEKANIZMA/YOL bos olamaz" % i)
            continue
        veri.append({
            "MEKANIZMA": mekanizma,
            "YOL": yol,
            "EV": ev,
            "SERIT": serit,
            "KABUL_KOMUTU": kabul_komutu,
            "SATIR_NO": i,
        })
    return veri, hatalar


def mekanizmaya_mekanizma_adlari(harita):
    """MEKANIZMA -> harita satiri. Birden fazla varsa ilk alinir (uyari: coklu)."""
    out = {}
    for h in harita:
        out.setdefault(h["MEKANIZMA"], h)
    return out


def _icerikten_ev(mekanizma, harita_index, stats):
    """4. adim (PAKET T3b): mutant dosyasinin metnini oku, tools/ referanslarini
    topla, haritadaki EV'lerinden tek ayirt edici olan varsa doner.

    Kurallar:
      - Kendi adi ve -test/-mutasyon turevleri haric tutulur (M7 onlemi).
      - BILINMIYOR olanlar atilir.
      - Tam olarak 1 ayirt edici EV → o EV.
      - SIFIR → BILINMIYOR (durust sonuc; sahipsiz KALIR).
      - BIRDEN COK ayrik EV → BILINMIYOR + stats["CAKISMA"]++ (mimara birakir).
      - Okuma IO/encoding hatasi → BILINMIYOR + stats["OKUNAMADI"]++ (sessiz 0 yasak).

    Fail-open YASAK: hicbir kosulda BILINMIYOR bir EV'e cevrilmez; secim mimarin isidir.
    """
    import re as _re
    try:
        with open(mekanizma, encoding="utf-8") as f:
            metin = f.read()
    except (OSError, UnicodeDecodeError):
        stats["OKUNAMADI"] = stats.get("OKUNAMADI", 0) + 1
        return "BILINMIYOR"

    # tools/<ad>.py ve tools/<ad>.js referanslari
    adaylar = set(_re.findall(r"tools/([a-zA-Z0-9_-]+\.(?:py|js))", metin))
    # Dosyanin KENDI referansini cikar (M7): hem tam ad, hem -test/-mutasyon turevleri
    baz = os.path.basename(mekanizma)
    kok_no_ext = baz[:-3] if baz.endswith(".py") else (baz[:-3] if baz.endswith(".js") else baz)
    haric = set()
    for t in (baz, kok_no_ext):
        haric.add(t)
        # -test / -mutasyon turevleri
        for ek in ("-test", "-mutasyon", "-mutasyon-test", "-prob"):
            haric.add(t + ek)
            haric.add(t + ek + ".py")
            haric.add(t + ek + ".js")
    adaylar -= haric
    if not adaylar:
        return "BILINMIYOR"

    # Her aday icin harita_index'te EV bul (kapi/kapisi.py/uzantisiz arama)
    evler = set()
    for a in sorted(adaylar):
        # a ornegi "abs-kapisi.py" — harita anahtari "abs-kapisi" (uzantisiz)
        # veya ".py" ile; bak.
        if a in harita_index:
            ev = harita_index[a]["EV"]
        elif a.endswith(".py") and a[:-3] in harita_index:
            ev = harita_index[a[:-3]]["EV"]
        elif a.endswith(".js") and a[:-3] in harita_index:
            ev = harita_index[a[:-3]]["EV"]
        elif (not a.endswith(".py")) and (a + ".py") in harita_index:
            ev = harita_index[a + ".py"]["EV"]
        elif (not a.endswith(".js")) and (a + ".js") in harita_index:
            ev = harita_index[a + ".js"]["EV"]
        else:
            continue
        if ev != "BILINMIYOR":
            evler.add(ev)
    if len(evler) == 1:
        return next(iter(evler))
    if len(evler) > 1:
        stats["CAKISMA"] = stats.get("CAKISMA", 0) + 1
    return "BILINMIYOR"


def mekanizma_icin_ev(mekanizma, harita_index, mutant_ayarlari=None,
                     repo_kok=None, stats=None):
    """Bir mekanizma adinin EV'sini haritadan coz. Kural:

      1) Mekanizma adinin kendisi haritada varsa: o satirin EV'si.
         (Harita anahtari .py'siz; "cta-denge-kapisi" — bu yuzden aramada
         .py ile ve .py'siz denenir.)
      2) "X-mutasyon.py" gibi bir mutant bataryasi icin: -mutasyon ekini
         atip olcutun kapisini ara: "X-kapisi" / "X-kapisi.py" (varsa onun
         EV'si), yoksa "X" / "X.py" (varsa onun EV'si). Bulunamazsa BILINMIYOR.
      3) -test/-prob turevleri: ayni kok ile dene.
      4) Icerikten EV (PAKET T3b): ad-ekseni ile cozulmediyse mutant dosyasinin
         metnini oku, tools/ referanslarinin haritadaki EV'lerinden TEK
         ayirt edici olan varsa onu doner. SIFIR → BILINMIYOR; BIRDEN COK →
         BILINMIYOR + stats["CAKISMA"]++ (mimara birakir). IO/encoding hatasi
         OKUNAMADI++.

    mutant_ayarlari: opsiyonel dict; "ev_override" verilmisse o kullanilir (M1).
    stats: opsiyonel sayac dict; COZULDU_ICERIKTEN/CAKISMA/OKUNAMADI icin.
    repo_kok: 4. adim icin mutlak yol cozumlemede kullanilir.
    """
    if mutant_ayarlari and "ev_override" in mutant_ayarlari:
        return mutant_ayarlari["ev_override"]
    if stats is None:
        stats = {}
    ad = mekanizma

    def _bak(aday):
        """Harita_index'te aday ya da .py'li/eksiz varyantini ara."""
        if aday in harita_index:
            return harita_index[aday]["EV"]
        if aday.endswith(".py") and aday[:-3] in harita_index:
            return harita_index[aday[:-3]]["EV"]
        if (not aday.endswith(".py")) and (aday + ".py") in harita_index:
            return harita_index[aday + ".py"]["EV"]
        return None

    # 1) Dogrudan eslesme
    ev = _bak(ad)
    if ev is not None:
        return ev
    # 2) Mutant bataryasi eslestirmesi
    #    Dosya adi "cta-denge-mutasyon.py" — kok = "cta-denge", ek = "-mutasyon.py"
    #    (basinda tire ile; bu yuzden kok tire-siz cikar).
    if ad.endswith("-mutasyon.py"):
        kok = ad[:-len("-mutasyon.py")]
        for a in (kok + "-kapisi", kok + "-kapisi.py",
                  kok, kok + ".py"):
            ev = _bak(a)
            if ev is not None:
                return ev
    # -prob.md / -test.py gibi diger test altyapilari da haritanin evreninde yok
    # ama bir kapisi olabilir; ayni kok ile dene.
    for ek in ("-test.py", "-mutasyon-test.py", "-prob.md"):
        if ad.endswith(ek):
            kok = ad[:-len(ek)]
            for a in (kok + "-kapisi", kok + "-kapisi.py",
                      kok, kok + ".py"):
                ev = _bak(a)
                if ev is not None:
                    return ev
    # 4) Icerikten EV (PAKET T3b) — yalniz BILINMIYOR kalanlara uygulanir.
    #    Onceki adimlar eski davranisi degistirmez; yalniz BILINMIYOR kalan
    #    mekanizmalar icin ek bir sans verilir.
    #    Dosya yolu: gercek mutant dosyalari tools/ altinda; adim hem
    #    "repo_kok/<ad>" hem "repo_kok/tools/<ad>" dener.
    if repo_kok and ad.endswith("-mutasyon.py"):
        tam = ad if os.path.isabs(ad) else os.path.join(repo_kok, ad)
        if not os.path.isfile(tam):
            alt = os.path.join(repo_kok, "tools", ad)
            if os.path.isfile(alt):
                tam = alt
        if os.path.isfile(tam):
            ev = _icerikten_ev(tam, harita_index, stats)
            if ev != "BILINMIYOR":
                stats["COZULDU_ICERIKTEN"] = stats.get("COZULDU_ICERIKTEN", 0) + 1
                return ev
    return "BILINMIYOR"


def ev_adresi(ev, koku_root=None):
    """Bir EV icin posta kutusu yolunu doner. koku_root verilmisse (--kendini-test
    izolasyonu) o kokun ALTINDA <EV>/memory/mimar-posta-kutusu.md'ye yazilir.
    Gercek modda EV_DIZIN[ev] kullanilir.

    Return: (proje_koku, mimar_posta_kutusu_yolu, EV_gecerli_mi).
    EV=BILINMIYOR ise proje_koku=None doner (cagri yazmaz; sadece KraL'da
    DEVREDILDI notu birakir).
    """
    if ev == "BILINMIYOR":
        return None, None, False
    if ev not in EV_BILINEN:
        return None, None, False
    if koku_root is not None:
        # Izolasyon: tum EV'ler ayni tempdir altinda EV alt-dizinli
        posta_yol = os.path.join(koku_root, ev, POSTA_DOSYA)
        return koku_root, posta_yol, True
    kok = EV_DIZIN.get(ev)
    if kok is None:
        return None, None, False
    return kok, os.path.join(kok, POSTA_DOSYA), True


# ------------------------------------------------------------------------------
# POSTA KUTUSU yardimcilari
# ------------------------------------------------------------------------------
def _posta_var_mi(yol):
    return os.path.isfile(yol)


def _posta_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _posta_yaz_atomik(yol, icerik):
    """Atomik yaz: gecici + os.replace. IOError -> exception raise."""
    dizin = os.path.dirname(yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".t3-posta-", dir=dizin or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(icerik)
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def _posta_satir_ekle(yol, satir):
    """Varolan dosyanin sonuna bir satir ekler; yoksa olusturur. Atomik."""
    mevcut = _posta_oku(yol) if _posta_var_mi(yol) else ""
    if mevcut and not mevcut.endswith("\n"):
        mevcut += "\n"
    yeni = mevcut + satir + "\n"
    _posta_yaz_atomik(yol, yeni)


def _posta_satir_sil(yol, damga):
    """Verilen damga ile baslayan (DEVREDILDI ya da sentetik) satirlari sil.

    Birden fazla eslesen satiri siler; dosya degisti mi kanit olarak doner.
    """
    if not _posta_var_mi(yol):
        return False
    mevcut = _posta_oku(yol)
    satirlar = mevcut.split("\n")
    yeni = []
    silindi = False
    for s in satirlar:
        if damga in s:
            silindi = True
            continue
        yeni.append(s)
    yeni_metin = "\n".join(yeni)
    if yeni_metin and not yeni_metin.endswith("\n"):
        yeni_metin += "\n"
    if silindi:
        _posta_yaz_atomik(yol, yeni_metin)
    return silindi


# ------------------------------------------------------------------------------
# KALEM -> yonlendirme
# ------------------------------------------------------------------------------
def _damga():
    """Tekil bir damga uretir (zaman + pid). MUTANT tarafindan hedef damgayi
    kanitlamak icin ayni kosumda uretilen tum sentetik satirlar AYNI damgayi
    tasir (silme kaniti icin)."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "-pid%d" % os.getpid()


def krat_satir_yoksa_bul(repo_kok):
    """KraL'in acik-kalemler.md icinde 'DEVREDILDI' notu eklenecek satir
    bulunamayacagi icin burada KraL tarafi kullanilmiyor. Mecburiyet yok.
    Bu fonksiyon spec gereksinimi icin dis yuzey: yalnizca posta kutusuna
    DEVREDILDI notu yaziyoruz (KraL'in acik-kalemler'i BURADAN degil,
    baska bir paket tarafindan guncellenir)."""
    return None


def yonlendir(kalem, harita_index, koku_root=None, *, yazilamaz_yollar=None,
               repo_kok=None, stats=None):
    """Bir kalemi EV'sine yonlendir.

    kalem: {"mekanizma": str, "kosum_id": str, "kirmizi_adim": str,
            "kabul_komutu": str, "sahte_mi": str ("EVET"/"HAYIR"/"OLCULEMEDI"),
            "sentetik": bool (--tatbikat icin uretildi mi)}

    Dondurur:
      {
        "EV": str,
        "EV_KAYNAK": "HARITA"|"MUTANT_EV"|"ICERIKTEN"|"BILINMIYOR",
        "POSTA_YOL": str|None,
        "YAZILDI": bool,
        "DEVREDILDI_NOTU_KRAIL": bool,   # KraL'a yazilan DEVREDILDI notu (sadece KraL disi ise)
        "HATA": str|None,
        "SAHIPSIZ": bool,                 # BILINMIYOR ise True
        "DAMGA": str,
      }

    yazilamaz_yollar: set/None; icindeki yazilamaz (M3 simulasyonu).
    repo_kok: icerikten EV turetimi icin (PAKET T3b).
    stats: COZULDU_ICERIKTEN/CAKISMA/OKUNAMADI sayac dict.
    """
    damga = kalem.get("damga") or _damga()
    stats = stats if stats is not None else {}
    # Once-sonra sayac karsilastirmasi: bu kalem icerikten EV ile cozuldu mu?
    once = stats.get("COZULDU_ICERIKTEN", 0)
    ev = mekanizma_icin_ev(kalem["mekanizma"], harita_index,
                           mutant_ayarlari=kalem.get("mutant_ayar"),
                           repo_kok=repo_kok, stats=stats)
    sonra = stats.get("COZULDU_ICERIKTEN", 0)
    ev_kaynak = "HARITA"
    if kalem.get("mutant_ayar", {}).get("ev_override"):
        ev_kaynak = "MUTANT_EV"
    elif sonra > once and ev != "BILINMIYOR":
        ev_kaynak = "ICERIKTEN"

    sonuc = {
        "EV": ev,
        "EV_KAYNAK": ev_kaynak,
        "POSTA_YOL": None,
        "HEDEF_YAZILDI": False,
        "YAZILDI": False,
        "DEVREDILDI_NOTU_KRAIL": False,
        "IZ_YOL": None,
        "IZ_YAZILDI": None,
        "HATA": None,
        "SAHIPSIZ": (ev == "BILINMIYOR"),
        "DAMGA": damga,
        "MEKANIZMA": kalem["mekanizma"],
        "KOSUM_ID": kalem.get("kosum_id", ""),
        "KIRMIZI_ADIM": kalem.get("kirmizi_adim", ""),
        "KABUL_KOMUTU": kalem.get("kabul_komutu", ""),
        "SAHTE_MI": kalem.get("sahte_mi", "OLCULEMEDI"),
        "SENTETIK": kalem.get("sentetik", False),
    }

    # T3-SAHIPSIZ kolu: YALNIZ ev == "BILINMIYOR" icin konusur.
    # Kendi jetonunu mesajin BASINDA uretir; boylece M2 dogrulamasi
    # SAHIPSIZ bayragina degil, "T3-SAHIPSIZ " onekine baglanir (kol ayrimi).
    # ev_adresi()'nin gecersiz-EV donusu AYRI bir hata sinifi (T3-EV-GECERSIZ)
    # olarak asagida yakalanir; SAHIPSIZ ASLA True set edilmez.
    # Format: "<JETON> <govde>" — jeton ile govde arasinda BOSLUK (K183b).
    if ev == "BILINMIYOR":
        sonuc["HATA"] = ("T3-SAHIPSIZ haritada eslesme yok; "
                         "kalem MIMAR'da kaldi")
        return sonuc

    kok, posta_yol, gecerli = ev_adresi(ev, koku_root=koku_root)
    if not gecerli:
        # T3-EV-GECERSIZ: ev_adresi() gecersiz EV donusu. SAHIPSIZ bayragina
        # DOKUNMAZ (ASLA set etmez — kol sozlesmesi); mesaj T3-EV-GECERSIZ
        # onekiyle baslar ki M2'nin "T3-SAHIPSIZ " onekini arayan dogrulamasi
        # bu mesaji T3-SAHIPSIZ olarak YAKALAMASIN (kol ayrimi).
        sonuc["HATA"] = ("T3-EV-GECERSIZ ev gecersiz: %r" % ev)
        return sonuc
    sonuc["POSTA_YOL"] = posta_yol

    # T3-OLCULEMEDI kolu: hedef kutuya yazilamaz (M3 simulasyonu veya IO).
    # Mesaj T3-OLCULEMEDI onekiyle baslar; kol ayrimi.
    if yazilamaz_yollar and posta_yol in yazilamaz_yollar:
        sonuc["HATA"] = "T3-OLCULEMEDI hedef kutu yazilamaz (M3 simulasyonu)"
        return sonuc

    # Satiri hedef posta kutusuna yaz.
    sentetik_isaret = "SENTETIK" if kalem.get("sentetik") else "GERCEK"
    satir = ("%s | mekanizma=%s | koşum=%s | kirmizi=%s | kabul=%s | "
             "sahte_mi=%s | sentetik=%s | ev=%s | ev_kaynak=%s"
             % (damga, kalem["mekanizma"], kalem.get("kosum_id", "-"),
                kalem.get("kirmizi_adim", "-"), kalem.get("kabul_komutu", "YOK"),
                kalem.get("sahte_mi", "OLCULEMEDI"), sentetik_isaret, ev, ev_kaynak))
    try:
        _posta_satir_ekle(posta_yol, satir)
        sonuc["HEDEF_YAZILDI"] = True
    except Exception as e:
        sonuc["HATA"] = "T3-OLCULEMEDI hedef kutu yazma basarisiz: %r" % e
        return sonuc

    # T3-IZ kolu: DEVREDILDI izi (EV != KraL ise KraL'in posta kutusuna TEK
    # satir). Yazma BASARISIZSA fail-closed: YAZILDI True KALMAZ.
    # Mesaj T3-IZ onekiyle baslar; kol ayrimi.
    if ev != "KraL":
        kral_kok, kral_posta_yol, kral_gecerli = ev_adresi("KraL", koku_root=koku_root)
        sonuc["IZ_YOL"] = kral_posta_yol
        if not kral_gecerli:
            sonuc["HATA"] = "T3-IZ DEVREDILDI izi yazilamadi (KraL kutu gecersiz)"
            sonuc["YAZILDI"] = False
            sonuc["DEVREDILDI_NOTU_KRAIL"] = False
            sonuc["IZ_YAZILDI"] = False
            return sonuc
        # M4 simulasyonu: KraL'in posta kutusu yazilamaz.
        if yazilamaz_yollar and kral_posta_yol in yazilamaz_yollar:
            sonuc["HATA"] = ("T3-IZ DEVREDILDI izi yazilamadi (M4 simulasyonu)")
            sonuc["YAZILDI"] = False
            sonuc["DEVREDILDI_NOTU_KRAIL"] = False
            sonuc["IZ_YAZILDI"] = False
            return sonuc
        # DEVREDILDI iz satiri (KraL'in defterine dusur; satir silinmez).
        iz_satir = ("DEVREDILDI: %s | mekanizma=%s | kosum=%s | damga=%s"
                    % (ev, kalem["mekanizma"],
                       kalem.get("kosum_id", "-"), damga))
        try:
            _posta_satir_ekle(kral_posta_yol, iz_satir)
            sonuc["IZ_YAZILDI"] = True
            sonuc["DEVREDILDI_NOTU_KRAIL"] = True
        except Exception as e:
            sonuc["HATA"] = ("T3-IZ DEVREDILDI izi yazilamadi: %r" % e)
            sonuc["YAZILDI"] = False
            sonuc["DEVREDILDI_NOTU_KRAIL"] = False
            sonuc["IZ_YAZILDI"] = False
            return sonuc

    # Tum adimlar OK; YAZILDI=True.
    sonuc["YAZILDI"] = True
    return sonuc


def temizle_sentetik(yonlendirme_sonuclari, koku_root=None):
    """Sentetik olarak isaretlenmis satirlari posta kutularindan sil.

    Izolasyon modunda (koku_root verilmis) tum EV alt-dizinlerini gez; gercek
    modda EV_DIZIN uzerinden.

    Dondurur: dict {posta_yol: silindi_mi_bool, ...}
    """
    damgalar = {s["DAMGA"] for s in yonlendirme_sonuclari if s.get("SENTETIK")}
    if not damgalar:
        return {}
    yollar = []
    if koku_root is not None:
        # Izolasyon: her EV ayri alt dizinde
        for ev in EV_BILINEN:
            yollar.append(os.path.join(koku_root, ev, POSTA_DOSYA))
    else:
        # EV_DIZIN'de KraL/BaBa/ORTAK ayni kok; tekrari onle.
        gorulen = set()
        for kok in EV_DIZIN.values():
            yol = os.path.join(kok, POSTA_DOSYA)
            if yol in gorulen:
                continue
            gorulen.add(yol)
            yollar.append(yol)
    out = {}
    for yol in yollar:
        for d in damgalar:
            sildi = _posta_satir_sil(yol, d)
            out[yol] = out.get(yol, False) or sildi
    return out


# ------------------------------------------------------------------------------
# MUTANT ALTYAPISI (--kendini-test)
# ------------------------------------------------------------------------------
def _gvd_yedekle(yol):
    yedek = yol + ".kendinitest-yedek"
    with open(yol, encoding="utf-8") as f, open(yedek, "w", encoding="utf-8") as g:
        g.write(f.read())
    return yedek


def _gvd_yedekten_geri(yol, yedek):
    with open(yedek, encoding="utf-8") as f, open(yol, "w", encoding="utf-8") as g:
        g.write(f.read())
    os.unlink(yedek)


def _mutant_ev_degistir(tsv_yolu, mekanizma_adi, yeni_ev):
    """M1: haritadaki bir satirin EV kolonunu gecici olarak degistir."""
    satirlar = open(tsv_yolu, encoding="utf-8").read().splitlines()
    out = []
    degisti = False
    for s in satirlar:
        if (not s.strip() or s.lstrip().startswith("#")
                or s.startswith("MEKANIZMA")):
            out.append(s)
            continue
        kol = s.split("\t")
        if len(kol) >= 3 and kol[0].strip() == mekanizma_adi and not degisti:
            kol[2] = yeni_ev
            degisti = True
            out.append("\t".join(kol))
            continue
        out.append(s)
    with open(tsv_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return degisti


def kendini_test(repo_kok, harita_yolu, koku_root):
    """4 mutant + izolasyon. Her biri hedef kolunu AYRICA kanitlar.

    koku_root: --kendini-test'te tempfile.mkdtemp(); gercek posta kutularina
    DOKUNULMAZ.

    KABUL: MUTANT=4/4, T3-YON, T3-SAHIPSIZ, T3-OLCULEMEDI, T3-IZ gecti,
    SAHIPSIZ sayaci ayri basildi, TEMIZ=EVET kanitlandi.
    """
    tsv = os.path.join(repo_kok, harita_yolu) if not os.path.isabs(harita_yolu) else harita_yolu
    if not os.path.isfile(tsv):
        print("HATA: harita dosyasi yok: " + tsv)
        return 1
    yedek = _gvd_yedekle(tsv)
    try:
        harita, _ = haritayi_oku(repo_kok, harita_yolu)
        harita_index = mekanizmaya_mekanizma_adlari(harita)

        adimlar = []
        # Tek damga — sentetik tum mutantlar AYNI damga ile uretilir; temizlik
        # tek seferde kanitlanir.
        ortak_damga = "T3TEST-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        # --- M1: haritada r2-purge EV'si MaCiT -> ArTisT olsun -----------------
        # Beklenen: kalem ArTisT kutusuna yazilir, T3-YON kolu mesaj verir.
        _mutant_ev_degistir(tsv, "r2-purge", "ArTisT")
        harita1, _ = haritayi_oku(repo_kok, harita_yolu)
        idx1 = mekanizmaya_mekanizma_adlari(harita1)
        kalem_m1 = {
            "mekanizma": "r2-purge",
            "kosum_id": "kosum-M1-test",
            "kirmizi_adim": "M1.adim",
            "kabul_komutu": "python3 tools/r2-purge-test.py",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        sonuc_m1 = yonlendir(kalem_m1, idx1, koku_root=koku_root)
        # Izolasyon: ArTisT altinda /<koku_root>/ArTisT/memory/... olmali.
        m1_yazildi_artistte = (
            sonuc_m1["EV"] == "ArTisT"
            and sonuc_m1["YAZILDI"]
            and sonuc_m1["POSTA_YOL"] == os.path.join(koku_root, "ArTisT", POSTA_DOSYA)
        )
        # T3-YON kolunun mesaji: EV cozumleme haritadan OKUNDU (sabit degil).
        t3_yon_mesaj = ("EV=ArTisT (MUTANT_EV)" if sonuc_m1["EV_KAYNAK"] == "MUTANT_EV"
                        else "EV=%s" % sonuc_m1["EV"])
        m1_reddetti = m1_yazildi_artistte
        adimlar.append(("M1", T3_YON_JETON, m1_reddetti, t3_yon_mesaj,
                        sonuc_m1))
        _gvd_yedekten_geri(tsv, yedek)
        yedek = _gvd_yedekle(tsv)

        # --- M2: mekanizma haritada YOK ---------------------------------------
        # Beklenen: BILINMIYOR + kalem MIMAR'da KALIR + HATA `T3-SAHIPSIZ ` oneki.
        # Dogrulama SAHIPSIZ bayragina degil, hedef kolun KENDI mesajina bakinir
        # (kol ayrimi); boylece T3-SAHIPSIZ govdesi oldurulurse M2 burada
        # mutant YASAMAZ (kirmizi kalir).
        kalem_m2 = {
            "mekanizma": "hayalet-mekanizma-yok-12345",
            "kosum_id": "kosum-M2-test",
            "kirmizi_adim": "M2.adim",
            "kabul_komutu": "YOK",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        sonuc_m2 = yonlendir(kalem_m2, idx1, koku_root=koku_root)
        m2_sahipsiz = (
            sonuc_m2["EV"] == "BILINMIYOR"
            and sonuc_m2["SAHIPSIZ"] is True
            and sonuc_m2["YAZILDI"] is False
            and sonuc_m2["HATA"] is not None
            and sonuc_m2["HATA"].startswith(T3_SAHIPSIZ_JETON + " ")
        )
        t3_sahipsiz_mesaj = ("EV=BILINMIYOR HATA=T3-SAHIPSIZ: "
                             "haritada eslesme yok (MIMAR'da kaldi)")
        m2_reddetti = m2_sahipsiz
        adimlar.append(("M2", T3_SAHIPSIZ_JETON, m2_reddetti, t3_sahipsiz_mesaj,
                        sonuc_m2))

        # --- M3: hedef kutuya yazma BASARISIZ --------------------------------
        # Beklenen: tatbikat KIRMIZI + OLCULEMEDI; "teslim edildi" DEMEZ.
        # Mesaj `T3-OLCULEMEDI ` onekiyle baslar (kol ayrimi).
        # Simulasyon: posta kutusu yolunu yazilamaz_yollar'a ekle.
        ev_can = "MaCiT"
        kok_m3, yol_m3, _ = ev_adresi(ev_can, koku_root=koku_root)
        yazilamaz = {yol_m3}
        # r2-purge icin (gercek haritaya gore) EV=MaCiT; M3 icin MaCiT yazilamaz.
        kalem_m3 = {
            "mekanizma": "r2-purge",
            "kosum_id": "kosum-M3-test",
            "kirmizi_adim": "M3.adim",
            "kabul_komutu": "python3 tools/r2-purge-test.py",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        # Haritayi geri yukle (M1 revert ettik), r2-purge MaCiT olsun.
        harita2, _ = haritayi_oku(repo_kok, harita_yolu)
        idx2 = mekanizmaya_mekanizma_adlari(harita2)
        sonuc_m3 = yonlendir(kalem_m3, idx2, koku_root=koku_root, yazilamaz_yollar=yazilamaz)
        m3_olculemedi = (
            sonuc_m3["YAZILDI"] is False
            and sonuc_m3["HATA"] is not None
            and sonuc_m3["HATA"].startswith(T3_OLCULEMEDI_JETON + " ")
        )
        t3_olculemedi_mesaj = ("EV=%s YAZILDI=False HATA=T3-OLCULEMEDI "
                               "(fail-closed)" % sonuc_m3["EV"])
        m3_reddetti = m3_olculemedi
        adimlar.append(("M3", T3_OLCULEMEDI_JETON, m3_reddetti, t3_olculemedi_mesaj,
                        sonuc_m3))

        # --- M4: KraL'in posta kutusuna DEVREDILDI izi yazilamaz --------------
        # Beklenen: MaCiT yazildi, ama KraL izi yazilamadi → YAZILDI=False,
        # HATA `T3-IZ ` onekiyle baslar (kol ayrimi; OLCULEMEDI degil).
        # Kurulum: yazilamaz_yollar = {KraL mailbox path} (gercek arsiv adresi).
        _, kral_posta_yol_m4, _ = ev_adresi("KraL", koku_root=koku_root)
        yazilamaz_m4 = {kral_posta_yol_m4}
        # r2-purge MaCiT (gercek harita MaCiT).
        harita4, _ = haritayi_oku(repo_kok, harita_yolu)
        idx4 = mekanizmaya_mekanizma_adlari(harita4)
        kalem_m4 = {
            "mekanizma": "r2-purge",
            "kosum_id": "kosum-M4-test",
            "kirmizi_adim": "M4.adim",
            "kabul_komutu": "python3 tools/r2-purge-test.py",
            "sahte_mi": "EVET",
            "sentetik": True,
            "damga": ortak_damga,
        }
        sonuc_m4 = yonlendir(kalem_m4, idx4, koku_root=koku_root,
                             yazilamaz_yollar=yazilamaz_m4)
        m4_iz_yazilamadi = (
            sonuc_m4["HEDEF_YAZILDI"] is True
            and sonuc_m4["YAZILDI"] is False
            and sonuc_m4["HATA"] is not None
            and sonuc_m4["HATA"].startswith(T3_IZ_JETON + " ")
            and "DEVREDILDI" in sonuc_m4["HATA"]
        )
        t3_iz_mesaj = ("EV=%s HEDEF_YAZILDI=True YAZILDI=False "
                       "HATA=T3-IZ: DEVREDILDI izi yazilamadi (fail-closed)"
                       % sonuc_m4["EV"])
        m4_reddetti = m4_iz_yazilamadi
        adimlar.append(("M4", T3_IZ_JETON, m4_reddetti, t3_iz_mesaj,
                        sonuc_m4))

        # --- TEMIZLIK KANITI --------------------------------------------------
        # Tum sentetik kalemleri AYNI damga ile urettik; temizlik kanitla.
        # Burada temizle_sentetik() gercek koklerdeki dosyalari da gezer; ama
        # --kendini-test'te koku_root gecici oldugu icin gercek koklerde hicbir
        # damga eslesmez ve silinmez. Yine de guvenli: bostan yazma yok.
        temizle_sonuc = temizle_sentetik([s for _, _, _, _, s in adimlar],
                                         koku_root=koku_root)
        # Izole kokte gercekten yazip yazmadigimizi kontrol et: dosya var mi?
        ortak_dosya = os.path.join(koku_root, POSTA_DOSYA)
        # Sentetik damga, izole kokte yazildiysa, temizlik sonrasi kalmamali.
        temizlik_ok = True
        if os.path.isfile(ortak_dosya):
            icerik = open(ortak_dosya, encoding="utf-8").read()
            if ortak_damga in icerik:
                temizlik_ok = False
        # Ek: alt dizinlerde de (ArTisT, MaCiT, KraL) damga kalmasin.
        for ev in ("ArTisT", "MaCiT", "KraL"):
            alt = os.path.join(koku_root, ev, POSTA_DOSYA)
            if os.path.isfile(alt):
                if ortak_damga in open(alt, encoding="utf-8").read():
                    temizlik_ok = False

        # ---- ozet bas -------------------------------------------------------
        print("T3 YONLENDIRME KAPISI — KENDINI-TEST")
        print("izolasyon koku (posta kutulari): %s" % koku_root)
        print("ortak damga: %s" % ortak_damga)
        print("")
        mutant_sayaci = 0
        for ad, jeton, gecti, mesaj, sonuc in adimlar:
            print("MUTANT %s -> hedef kol %s" % (ad, jeton))
            print("  mesaj: %s" % mesaj)
            print("  EV=%s HEDEF_YAZILDI=%s YAZILDI=%s SAHIPSIZ=%s HATA=%r"
                  % (sonuc["EV"], sonuc.get("HEDEF_YAZILDI"),
                     sonuc["YAZILDI"], sonuc["SAHIPSIZ"], sonuc["HATA"]))
            print("  POSTA_YOL=%s" % (sonuc["POSTA_YOL"] or "(yok)"))
            if "IZ_YOL" in sonuc and sonuc["IZ_YOL"]:
                print("  IZ_YOL=%s IZ_YAZILDI=%s"
                      % (sonuc["IZ_YOL"], sonuc.get("IZ_YAZILDI")))
            if gecti:
                print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
                mutant_sayaci += 1
            else:
                print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
            print("")

        # SAHIPSIZ sayaci (sadece M2'yi saymaz; bu turda analiz kisminda da
        # sayilir; burada M2'nin BEKLENTISI BILINMIYOR uretmesi).
        print("SAHIPSIZ=%d" % sum(1 for _, _, _, _, s in adimlar if s["SAHIPSIZ"]))
        # TEMIZ kaniti: izolasyon kokundeki gercek posta kutusu dosyasi yoksa
        # ya da damga yoksa TEMIZ=EVET; aksi TEMIZ=OLCULEMEDI.
        if temizlik_ok:
            print("TEMIZ=EVET")
        else:
            print("TEMIZ=OLCULEMEDI")
        print("")
        print("MUTANT=%d/4" % mutant_sayaci)
        if mutant_sayaci == 4 and temizlik_ok:
            return 0
        return 1
    finally:
        if yedek and os.path.isfile(yedek):
            try:
                _gvd_yedekten_geri(tsv, yedek)
            except OSError:
                pass


def kendini_test_butun(repo_kok, harita_yolu, koku_root):
    """M1-M4 (4 eski mutant) + M5-M7 (3 yeni mutant) + K3, K4 (2 kontrol).

    M1-M4 mevcut izolasyonlu test; M5-M7 + K3/K4 sentetik fiksturde.
    Toplam kabul: MUTANT=7/7 + KONTROL=2/2 + TEMIZ=EVET.
    """
    # Once M1-M4 (eski gerileme nobeti)
    rc_eski = kendini_test(repo_kok, harita_yolu, koku_root)
    # Sonra M5-M7 + K3/K4 (yeni)
    print("")
    m5_7_sayaci, k3_4_sayaci, hata = paket_t3b_mutant_test(repo_kok)
    print("M5-M7=%d/3 K3-K4=%d/2" % (m5_7_sayaci, k3_4_sayaci))
    if rc_eski != 0 or m5_7_sayaci != 3 or k3_4_sayaci != 2:
        return 1
    return 0


# ------------------------------------------------------------------------------
# PAKET T3b — M5/M6/M7 + K3/K4 (sentetik fikstur; gercek haritaya DOKUNMAZ)
# ------------------------------------------------------------------------------
def paket_t3b_mutant_test(repo_kok):
    """PAKET T3b: 3 yeni mutant (M5/M6/M7) + 2 kontrol (K3, K4).

    Sentetik fikstur kullanir: tempfile.mkdtemp() altinda sentetik harita + sentetik
    mutant dosyalari. Gercek tools/sahiplik-haritasi.tsv'e DOKUNMAZ.

    M5: coklu ayrik EV'de sessiz ILKINI secseydi mutant YASARDI.
        Kirmizi: CAKISMA vakasi; tekil-EV kolu YESIL.
    M6: sifir aday kalinca varsayilan bir EV donseydi mutant YASARDI.
        Kirmizi: SAHIPSIZ korunur; COZULDU_ICERIKTEN YESIL.
    M7: oz-referans taramaya katilsaydi (self-ref-mutasyon haritada -> KraL),
        self-ref + bilgi-kapisi = KraL+MaCiT = CAKISMA uretirdi. Duzeltme: self
        haric tutulur → tek bilgi-kapisi → MaCiT. Kirmizi: oz-referans haric;
        CAKISMA kolu YESIL.
    K3: ad ekseninden ZATEN cozulen bir mekanizma icin 4. adim devreye
        GIRMEZ (EV DEGISMEZ); COZULDU_ICERIKTEN artmaz.
    K4: haritada olmayan X-mutasyon icin 4. adim BEKLENEN EV'yi bulur.

    Dondurur: (mutant_sayaci, kontrol_sayaci, hata_mesaji)
    """
    fikstur = tempfile.mkdtemp(prefix="t3b-fikstur-")
    try:
        fikstur_tools = os.path.join(fikstur, "tools")
        os.makedirs(fikstur_tools, exist_ok=True)

        # --- Sentetik harita (v1: coklu EV + tekil EV + bilgi-kapisi) ---
        sentetik_tsv = os.path.join(fikstur, "harita.tsv")
        with open(sentetik_tsv, "w", encoding="utf-8") as f:
            f.write("MEKANIZMA\tYOL\tEV\tSERIT\tKABUL_KOMUTU\n")
            f.write("KraL-tool-1\tKraL-tool-1.py\tKraL\tA\tpython3 tools/KraL-tool-1-test.py\n")
            f.write("MaCiT-tool-2\tMaCiT-tool-2.py\tMaCiT\tV\tpython3 tools/MaCiT-tool-2-test.py\n")
            f.write("bilgi-kapisi\tbilgi-kapisi.py\tMaCiT\tV\tpython3 tools/bilgi-kapisi-test.py\n")
            f.write("r2-purge\tr2-purge.py\tMaCiT\tV\tpython3 tools/r2-purge-test.py\n")

        # --- Sentetik mutant dosyalari -----------------------------------
        # M5: coklu ayrik EV
        multi_ev = os.path.join(fikstur_tools, "multi-ev-mutasyon.py")
        with open(multi_ev, "w", encoding="utf-8") as f:
            f.write("# multi-ev sentetik\n")
            f.write("tools/KraL-tool-1.py\n")
            f.write("tools/MaCiT-tool-2.py\n")
        # M5 karsilastirma: tekil EV
        single_ev = os.path.join(fikstur_tools, "single-ev-mutasyon.py")
        with open(single_ev, "w", encoding="utf-8") as f:
            f.write("tools/KraL-tool-1.py\n")
        # M6: hic referans yok
        no_ev = os.path.join(fikstur_tools, "no-ev-mutasyon.py")
        with open(no_ev, "w", encoding="utf-8") as f:
            f.write("# hic referans yok\n")
        # M6 karsilastirma: gecerli tek EV
        valid_ev = os.path.join(fikstur_tools, "valid-ev-mutasyon.py")
        with open(valid_ev, "w", encoding="utf-8") as f:
            f.write("tools/bilgi-kapisi.py\n")
        # M7: oz-referans + gecerli ref
        self_ref = os.path.join(fikstur_tools, "self-ref-mutasyon.py")
        with open(self_ref, "w", encoding="utf-8") as f:
            f.write("# kendi adini + gecerli ref\n")
            f.write("tools/self-ref-mutasyon.py\n")
            f.write("tools/bilgi-kapisi.py\n")
        # K3: haritada ZATEN cozulen bir mekanizma (ad-ekseni)
        k3_direkt = os.path.join(fikstur_tools, "r2-purge-mutasyon.py")
        with open(k3_direkt, "w", encoding="utf-8") as f:
            f.write("tools/r2-purge.py\n")
        # K4: haritada olmayan X-mutasyon; icerigi X-kapisi.py'ye yonlendirir
        k4_indirect = os.path.join(fikstur_tools, "indirect-mutasyon.py")
        with open(k4_indirect, "w", encoding="utf-8") as f:
            f.write("tools/bilgi-kapisi.py\n")

        # M7 icin ozel harita: self-ref-mutasyon -> KraL (bilgi-kapisi -> MaCiT)
        # Duzeltme: self-ref haric tutulursa EV=MaCiT; bug'da KraL+MaCiT CAKISMA
        sentetik_tsv_2 = os.path.join(fikstur, "harita2.tsv")
        with open(sentetik_tsv_2, "w", encoding="utf-8") as f:
            f.write("MEKANIZMA\tYOL\tEV\tSERIT\tKABUL_KOMUTU\n")
            f.write("bilgi-kapisi\tbilgi-kapisi.py\tMaCiT\tV\tpython3 tools/bilgi-kapisi-test.py\n")
            f.write("self-ref-mutasyon\tself-ref-mutasyon.py\tKraL\tA\tpython3 tools/self-ref-mutasyon-test.py\n")

        # --- Haritayi oku -----------------------------------------------
        harita, _ = haritayi_oku(fikstur, "harita.tsv")
        harita_index = mekanizmaya_mekanizma_adlari(harita)
        harita2, _ = haritayi_oku(fikstur, "harita2.tsv")
        harita_index2 = mekanizmaya_mekanizma_adlari(harita2)

        adimlar = []

        # --- M5: coklu ayrik EV'de sessiz secim --------------------------
        # Buggy: BILINMIYOR yerine ILK EV (KraL) dondururdu.
        # Duzeltme: BILINMIYOR + CAKISMA=1.
        stats = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc = _icerikten_ev(multi_ev, harita_index, stats)
        m5_kirmizi = (sonuc == "BILINMIYOR" and stats["CAKISMA"] == 1)
        # Yan eksen: tekil-EV kolu YESIL kalmali (KraL donebilmeli).
        stats_tekil = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc_tek = _icerikten_ev(single_ev, harita_index, stats_tekil)
        m5_tekil_yesil = (sonuc_tek == "KraL" and stats_tekil["CAKISMA"] == 0)
        m5_hedef_kol_atfi = (m5_kirmizi and m5_tekil_yesil)
        m5_mesaj = ("EV=BILINMIYOR CAKISMA=1 (KIRMIZI); tekil test EV=KraL "
                    "CAKISMA=0 (YESIL)")
        adimlar.append(("M5", "CAKISMA", m5_hedef_kol_atfi, m5_mesaj, {
            "BILINMIYOR_BEKLENEN": sonuc, "CAKISMA": stats["CAKISMA"],
            "TEKIL_EV": sonuc_tek, "TEKIL_CAKISMA": stats_tekil["CAKISMA"],
        }))

        # --- M6: sifir adayda varsayilan EV dondur -----------------------
        # Buggy: BILINMIYOR yerine varsayilan EV (KraL) dondururdu.
        # Duzeltme: BILINMIYOR + COZULDU_ICERIKTEN degismez.
        stats = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc = _icerikten_ev(no_ev, harita_index, stats)
        m6_kirmizi = (sonuc == "BILINMIYOR" and stats["COZULDU_ICERIKTEN"] == 0)
        # Yan eksen: COZULDU_ICERIKTEN YESIL kalmali (gecerli ref test).
        stats_valid = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc_valid = _icerikten_ev(valid_ev, harita_index, stats_valid)
        m6_coz_yesil = (sonuc_valid == "MaCiT" and stats_valid["CAKISMA"] == 0)
        m6_hedef_kol_atfi = (m6_kirmizi and m6_coz_yesil)
        m6_mesaj = ("EV=BILINMIYOR COZULDU_ICERIKTEN=0 (KIRMIZI); gecerli ref "
                    "EV=MaCiT CAKISMA=0 (YESIL)")
        adimlar.append(("M6", "SAHIPSIZ", m6_hedef_kol_atfi, m6_mesaj, {
            "BILINMIYOR_BEKLENEN": sonuc, "COZULDU_NO": stats["COZULDU_ICERIKTEN"],
            "VALID_EV": sonuc_valid, "VALID_CAKISMA": stats_valid["CAKISMA"],
        }))

        # --- M7: oz-referans taramaya katilmasin ------------------------
        # Eger KENDI adi da katilmis olsaydi: self-ref-mutasyon -> KraL +
        # bilgi-kapisi -> MaCiT = 2 ayrik EV = CAKISMA. Duzeltme: self-ref
        # haric tutulur → sadece bilgi-kapisi → MaCiT.
        stats = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc = _icerikten_ev(self_ref, harita_index2, stats)
        m7_kirmizi = (sonuc == "MaCiT" and stats["CAKISMA"] == 0)
        # Yan eksen: CAKISMA kolu YESIL (coklu EV dosyasinda CAKISMA uretir).
        # harita_index2'de KraL-tool-1/MaCiT-tool-2 yok; harita_index kullan.
        stats_cakisma = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        sonuc_cak = _icerikten_ev(multi_ev, harita_index, stats_cakisma)
        m7_cakisma_yesil = (sonuc_cak == "BILINMIYOR" and stats_cakisma["CAKISMA"] >= 1)
        m7_hedef_kol_atfi = (m7_kirmizi and m7_cakisma_yesil)
        m7_mesaj = ("EV=MaCiT CAKISMA=0 (self-ref haric, KIRMIZI); "
                    "coklu-EV dosyasinda CAKISMA>=1 (YESIL)")
        adimlar.append(("M7", "OZ_REFERANS", m7_hedef_kol_atfi, m7_mesaj, {
            "SELF_EV": sonuc, "SELF_CAKISMA": stats["CAKISMA"],
            "CAKISMA_TEST_EV": sonuc_cak, "CAKISMA_TEST_CAKISMA": stats_cakisma["CAKISMA"],
        }))

        # --- K3: ad ekseninden ZATEN cozulen bir mekanizma DEGISMEZ -----
        # r2-purge-mutasyon.py -> "mutant bataryasi" turetme kurali (adim 2)
        # "r2-purge" EV'sini MaCiT olarak bulur; 4. adim devreye GIRMEZ.
        # Dogrulama: mekanizma_icin_ev EV=MaCiT donmeli; COZULDU_ICERIKTEN
        # ARTAMAZ (4. adim tetiklenmemis).
        stats_k3 = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        ev_k3 = mekanizma_icin_ev("r2-purge-mutasyon.py", harita_index,
                                 repo_kok=fikstur, stats=stats_k3)
        k3_yesil = (ev_k3 == "MaCiT" and stats_k3["COZULDU_ICERIKTEN"] == 0)
        k3_mesaj = ("EV=MaCiT (ad-ekseni); COZULDU_ICERIKTEN=0 (4. adim KAPALI)")
        adimlar.append(("K3", "AD_EKSEN_KORUMALI", k3_yesil, k3_mesaj, {
            "EV": ev_k3, "COZULDU_ICERIKTEN": stats_k3["COZULDU_ICERIKTEN"],
        }))

        # --- K4: haritada olmayan X-mutasyon icin 4. adim BEKLENEN EV -----
        # indirect-mutasyon.py haritada YOK; eski 1-2-3 adimlari da bulamaz
        # (kok "indirect" haritada yok). 4. adim icerikten bulmali → MaCiT.
        # Bu, gercek dunyadaki gercek BOYUTLU is gormezligi gibi: dosyanin
        # metni tek hedef kapiya isaret ediyor.
        stats_k4 = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}
        ev_k4 = mekanizma_icin_ev("indirect-mutasyon.py", harita_index,
                                 repo_kok=fikstur, stats=stats_k4)
        k4_yesil = (ev_k4 == "MaCiT" and stats_k4["COZULDU_ICERIKTEN"] == 1)
        k4_mesaj = ("EV=MaCiT (icerikten); COZULDU_ICERIKTEN=1")
        adimlar.append(("K4", "ICERIKTEN_GERCEK", k4_yesil, k4_mesaj, {
            "EV": ev_k4, "COZULDU_ICERIKTEN": stats_k4["COZULDU_ICERIKTEN"],
        }))

        # --- Ozet --------------------------------------------------------
        print("T3b YENI MUTANTLAR — sentetik fikstur: %s" % fikstur)
        print("gercek tools/sahiplik-haritasi.tsv'e DOKUNULMADI")
        print("")
        mutant_sayaci = 0
        kontrol_sayaci = 0
        for ad, jeton, gecti, mesaj, detay in adimlar:
            if ad.startswith("M"):
                etiket = "MUTANT"
            else:
                etiket = "KONTROL"
            print("%s %s -> hedef kol %s" % (etiket, ad, jeton))
            print("  mesaj: %s" % mesaj)
            print("  detay: %s" % detay)
            if gecti:
                print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
                if ad.startswith("M"):
                    mutant_sayaci += 1
                else:
                    kontrol_sayaci += 1
            else:
                print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
            print("")
        return mutant_sayaci, kontrol_sayaci, ""
    finally:
        shutil.rmtree(fikstur, ignore_errors=True)


# ------------------------------------------------------------------------------
# ANALIZ (default, yazmaz)
# ------------------------------------------------------------------------------
def analiz(repo_kok, harita_yolu, sahipsiz_listele=False):
    harita, hatalar = haritayi_oku(repo_kok, harita_yolu)
    if hatalar:
        print("HARITA OKUMA HATALARI:", file=sys.stderr)
        for h in hatalar:
            print("  " + h, file=sys.stderr)
    idx = mekanizmaya_mekanizma_adlari(harita)

    dagilim = {ev: 0 for ev in EV_BILINEN}
    dagilim["BILINMIYOR"] = 0
    dagilim_ev_kaynak = {"HARITA": 0, "MUTANT_EV": 0, "BILINMIYOR": 0}
    mutant_turevleri = []  # (mekanizma, EV, EV_kaynak)
    sahipsiz_listesi = []  # (mekanizma, kaynak) — BILINMIYOR olanlar
    stats = {"COZULDU_ICERIKTEN": 0, "CAKISMA": 0, "OKUNAMADI": 0}  # PAKET T3b

    # Mutasyon bataryalari haritanin evreninde yok; onlar icin ek cozumleme.
    ek_mekanizmalar = set()
    if os.path.isdir(os.path.join(repo_kok, "tools")):
        for f in sorted(os.listdir(os.path.join(repo_kok, "tools"))):
            if "-mutasyon" in f and f.endswith(".py") and not f.endswith("-test.py"):
                if f not in idx:
                    ek_mekanizmalar.add(f)

    for h in harita:
        ev = h["EV"]
        if ev in dagilim:
            dagilim[ev] += 1
        elif ev == "BILINMIYOR":
            dagilim["BILINMIYOR"] += 1
            sahipsiz_listesi.append((h["MEKANIZMA"], "HARITA"))

    for m in sorted(ek_mekanizmalar):
        ev = mekanizma_icin_ev(m, idx, repo_kok=repo_kok, stats=stats)
        if ev == "BILINMIYOR":
            dagilim["BILINMIYOR"] += 1
            mutant_turevleri.append((m, ev, "BILINMIYOR"))
            sahipsiz_listesi.append((m, "MUTANT_TUREV"))
        else:
            dagilim[ev] += 1
            mutant_turevleri.append((m, ev, "MUTANT_TUREV"))

    print("T3 YONLENDIRME KAPISI — ANALIZ (salt-okunur, YAZMAZ)")
    print("Repo: %s" % repo_kok)
    print("Harita: %s" % harita_yolu)
    print("")
    print("EV dagilimi (gercek harita + -mutasyon turevleri):")
    for ev in sorted(dagilim.keys()):
        print("  %-10s = %d" % (ev, dagilim[ev]))
    print("")
    print("SAHIPSIZ=%d (BILINMIYOR)" % dagilim["BILINMIYOR"])
    # SAHIPSIZ listesi (eslestirme kurali mimarindir; uydurma yok).
    if sahipsiz_listesi:
        print("")
        print("SAHIPSIZ_LISTESI (%d kayit, ADLAR):" % len(sahipsiz_listesi))
        for ad, kaynak in sahipsiz_listesi:
            print("  %-44s [%s]" % (ad, kaynak))
    if mutant_turevleri:
        print("")
        print("-mutasyon turevleri (haritada yok; -kapisi.py'nin EV'sine dustu):")
        for m, ev, kaynak in mutant_turevleri:
            print("  %-32s -> %s (%s)" % (m, ev, kaynak))
    # PAKET T3b: ozet EK satir (KAPI CI OZETI). SAYILAR KAYNAGINDAN.
    print("")
    print("SAHIPSIZ=%d COZULDU_ICERIKTEN=%d CAKISMA=%d OKUNAMADI=%d"
          % (dagilim["BILINMIYOR"],
             stats.get("COZULDU_ICERIKTEN", 0),
             stats.get("CAKISMA", 0),
             stats.get("OKUNAMADI", 0)))
    return 0


def sahipsiz_listele(repo_kok, harita_yolu):
    """Sadece SAHIPSIZ (BILINMIYOR) listesini bas; analiz ozetini atlar."""
    harita, hatalar = haritayi_oku(repo_kok, harita_yolu)
    if hatalar:
        print("HARITA OKUMA HATALARI:", file=sys.stderr)
        for h in hatalar:
            print("  " + h, file=sys.stderr)
    idx = mekanizmaya_mekanizma_adlari(harita)

    stats = {}
    sahipsiz = []
    for h in harita:
        if h["EV"] == "BILINMIYOR":
            sahipsiz.append((h["MEKANIZMA"], "HARITA"))
    ek_mekanizmalar = set()
    if os.path.isdir(os.path.join(repo_kok, "tools")):
        for f in sorted(os.listdir(os.path.join(repo_kok, "tools"))):
            if "-mutasyon" in f and f.endswith(".py") and not f.endswith("-test.py"):
                if f not in idx:
                    ek_mekanizmalar.add(f)
    for m in sorted(ek_mekanizmalar):
        if mekanizma_icin_ev(m, idx, repo_kok=repo_kok, stats=stats) == "BILINMIYOR":
            sahipsiz.append((m, "MUTANT_TUREV"))

    print("SAHIPSIZ=%d" % len(sahipsiz))
    for ad, kaynak in sahipsiz:
        print("  %-44s [%s]" % (ad, kaynak))
    # PAKET T3b: ozet EK satir (KAPI CI OZETI). SAYILAR KAYNAGINDAN.
    print("")
    print("SAHIPSIZ=%d COZULDU_ICERIKTEN=%d CAKISMA=%d OKUNAMADI=%d"
          % (len(sahipsiz),
             stats.get("COZULDU_ICERIKTEN", 0),
             stats.get("CAKISMA", 0),
             stats.get("OKUNAMADI", 0)))
    return 0


# ------------------------------------------------------------------------------
# TATBIKAT (gercek posta kutusu; AYNI kosumda siler)
# ------------------------------------------------------------------------------
def tatbikat(repo_kok, harita_yolu, temizlik=True):
    """Sentetik bir sahte kirmizi kalem uretip gercek posta kutusuna yazar.
    AYNI kosumda siler ve TEMIZ=EVET kanitlar.
    """
    harita, _ = haritayi_oku(repo_kok, harita_yolu)
    idx = mekanizmaya_mekanizma_adlari(harita)
    damga = "T3TATBIKAT-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    kalem = {
        "mekanizma": "r2-purge",
        "kosum_id": "kosum-tatbikat",
        "kirmizi_adim": "tatbikat.adim",
        "kabul_komutu": "python3 tools/r2-purge-test.py",
        "sahte_mi": "EVET",
        "sentetik": True,
        "damga": damga,
    }
    sonuc = yonlendir(kalem, idx, koku_root=None)
    print("TATBIKAT sonuc: EV=%s YAZILDI=%s HEDEF_YAZILDI=%s POSTA_YOL=%s"
          % (sonuc["EV"], sonuc["YAZILDI"], sonuc["HEDEF_YAZILDI"],
             sonuc["POSTA_YOL"]))
    if sonuc.get("IZ_YOL"):
        print("DEVREDILDI izi: IZ_YOL=%s IZ_YAZILDI=%s"
              % (sonuc["IZ_YOL"], sonuc.get("IZ_YAZILDI")))
    if temizlik:
        silinenler = temizle_sentetik([sonuc], koku_root=None)
        # Kanit: dosya hâlâ varsa icinde damga YOKMUs
        kanit_temiz = True
        for yol, sildi in silinenler.items():
            if os.path.isfile(yol):
                icerik = open(yol, encoding="utf-8").read()
                if damga in icerik:
                    kanit_temiz = False
        if kanit_temiz:
            print("TEMIZ=EVET (silinen dosyalar: %d)" % len([k for k, v in silinenler.items() if v]))
            return 0
        else:
            print("TEMIZ=OLCULEMEDI (damga hâlâ bir dosyada bulundu)")
            return 1
    return 0


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None,
                    help="repo koku (default: betigin konumundan turetilir)")
    ap.add_argument("--harita", default=HARITA_RELATIF,
                    help="harita TSV yolu (repo-goreli veya mutlak)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="M1-M4 + M5-M7 + K3/K4 mutan/kontrolleri izole kos "
                         "(gercek posta kutularina DOKUNMAZ)")
    ap.add_argument("--tatbikat", action="store_true",
                    help="sentetik kirmizi uretip gercek posta kutusuna yazar; "
                         "AYNI kosumda siler, TEMIZ=EVET kanitlar (hedef ev + "
                         "KraL DEVREDILDI izi dahil)")
    ap.add_argument("--temizlik-yapma", action="store_true",
                    help="--tatbikat ile: silme adimini atla (test icin)")
    ap.add_argument("--posta-koku-root", default=None,
                    help="--kendini-test icin izole posta kutusu koku "
                         "(default: tempfile.mkdtemp()). Belirtilmezse gecici dizin.")
    ap.add_argument("--sahipsiz-listele", action="store_true",
                    help="Sadece SAHIPSIZ (BILINMIYOR) listesini bas; "
                         "44 kaydin ADLARINI icerir.")
    args = ap.parse_args()

    repo_kok = args.repo or _repo_kok()

    if args.kendini_test:
        # Izolasyon: tempfile.mkdtemp() ASLA gercek posta kutusunu hedeflemez.
        koku = args.posta_koku_root or tempfile.mkdtemp(prefix="t3-kendinitest-")
        if not os.path.isdir(koku):
            try:
                os.makedirs(koku)
            except OSError as e:
                print("HATA: posta koku olusturulamadi: %r" % e)
                return 1
        # Gecici kok altinda hedef ev dizinleri olustur (MaCiT/ArTisT vs.)
        # ki M1 yazabilsin; bunlar yine de gecici.
        for ev in ("MaCiT", "ArTisT", "HocA", "TeKiN", "KraL"):
            os.makedirs(os.path.join(koku, ev, "memory"), exist_ok=True)
        rc = kendini_test_butun(repo_kok, args.harita, koku)
        # Is bitince gecici koku temizle (Okan diski).
        if not args.posta_koku_root:
            shutil.rmtree(koku, ignore_errors=True)
        return rc

    if args.tatbikat:
        return tatbikat(repo_kok, args.harita,
                        temizlik=not args.temizlik_yapma)

    if args.sahipsiz_listele:
        return sahipsiz_listele(repo_kok, args.harita)

    return analiz(repo_kok, args.harita)


if __name__ == "__main__":
    sys.exit(main())