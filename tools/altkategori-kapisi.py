#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `altkategori` (alt-filtre) veri yolu SESSIZ hata uretemez.

  python3 tools/altkategori-kapisi.py              # kabul (CI'da bloklayici)
  python3 tools/altkategori-kapisi.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/altkategori-kapisi.py --kok /yol   # modulleri/semayi BASKA agactan oku

NEDEN VAR (olculdu, 2026-08-01): `altkategori` alani urunler.json'da 100 kayitta DOLUYDU
ama HICBIR yerde islenmiyordu — index.html YOK, build.py YOK, d1-sync.py YOK, arama.py
YOK, d1-sema.sql YOK, duzelt.py'nin izinli alanlar listesinde YOK. Yani veri VARDI,
musteriye ULASMIYORDU ve kardes mimar alani mesru yoldan dolduramiyordu. Bu kapi o yolu
acilir tutar; yol yanlis acilirsa hata SESSIZDIR (musteri urune ulasamaz, alarm calmaz).

OLCULEN DORT SESSIZ-HATA SINIFI:
  A VERI   Kayittaki (kategori, altkategori) ikilisi tutarsiz olursa urun alt-filtrede
           YANLIS yere duser ya da HIC gorunmez; katalogda durdugu icin kimse fark etmez.
  B IMZA   Degerler bir TEDARIKCI VITRININDEN olculerek turetiliyor. Depo PUBLIC: deger
           marka/firma adi, alan adi, vitrin adi ya da urun kodu/SKU oneki tasirsa
           tedarikci iliskisi public repoya + siteye + D1'e SIZAR (ticari/hukuki risk).
           Deger GENEL Turkce kategori adi olmali. Kural BEYAZ LISTEDIR (gorulmemis imza
           turu sessizce gecmesin) — bkz. arama.altkategori_imza_sebebi.
  C YOL    duzelt.py alani yazamiyorsa veri ASLA dolmaz (bugunku tikanma); KOR yazabiliyorsa
           bilinmeyen deger sessizce kataloga girer. Ikisi de sessiz.
  D IKIZ   Ayni kolon BES yerde tanimli: d1-sema.sql (canli), d1-sync.GOC_KOLON (goc),
    TANIM  d1-sync._KT_SEMA (offline fikstur), satir_sql INSERT listesi, KOLONLAR
           (ON CONFLICT). Ustune bir de urun_hash KAPSAMI. Biri otekinden ayrisirsa
           testler YESIL yanarken canli baska semayla kosar / satir yeniden yazilmaz.

CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek d1-sema.sql ve gercek d1-sync fonksiyonlari
yerel bir sqlite3 kopyasinda kosturulur, gercek arama.urun_hash kullanilir, gercek duzelt.py
SENTETIK bir sahte repoda cagrilir. urunler.json yalnizca OKUNUR.
"""
import argparse
import hashlib
import importlib.util
import io
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


_KOLON_RE = re.compile(r"^([a-z_][a-z0-9_]*)\s+([A-Z]+)")


def sema_kolonlari(metin, tablo):
    """CREATE TABLE <tablo> govdesindeki {kolon: TIP}. Bulunamazsa bos sozluk."""
    m = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?%s\s*\(" % re.escape(tablo), metin)
    if not m:
        return {}
    i = m.end()
    derinlik = 1
    govde = []
    while i < len(metin) and derinlik:
        c = metin[i]
        if c == "(":
            derinlik += 1
        elif c == ")":
            derinlik -= 1
            if not derinlik:
                break
        govde.append(c)
        i += 1
    kolonlar = {}
    for satir in "".join(govde).split("\n"):
        satir = satir.split("--")[0].strip().rstrip(",")
        km = _KOLON_RE.match(satir)
        if km:
            kolonlar[km.group(1)] = km.group(2)
    return kolonlar


def insert_kolonlari(sql):
    """satir_sql ciktisindaki INSERT kolon listesi (sirali)."""
    m = re.search(r"INSERT INTO urunler \(([^)]*)\) VALUES", sql)
    return [k.strip() for k in m.group(1).split(",")] if m else []


def conflict_kolonlari(sql):
    return re.findall(r"(\w+)=excluded\.\w+", sql)


def _urun(uid, kategori="Marin", altkategori=None):
    u = {"id": uid, "baslik": "Deneme urun", "kategori": kategori, "marka": ["Marka"],
         "fiyat": "100 TL", "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"],
         "aciklama": "deneme"}
    if altkategori is not None:
        u["altkategori"] = altkategori
    return u


# ── SAHTE REPO (gercek duzelt.py'yi SENTETIK katalogda kosturur) ────────────────────
_SAHTE_KATALOG = [
    {"id": "alt-test-1", "kategori": "Marin", "marka": [], "baslik": "Marin urun",
     "aciklama": "a", "fiyat": "100 TL",
     "gorseller": ["https://media.pruvo3d.com/urunler/a-1.jpg"]},
    {"id": "alt-test-2", "kategori": "Ev", "marka": [], "baslik": "Ev urun",
     "aciklama": "b", "fiyat": "200 TL",
     "gorseller": ["https://media.pruvo3d.com/urunler/b-1.jpg"]},
]


def sahte_repo(kok):
    d = tempfile.mkdtemp(prefix="altkategori-kapisi-")
    os.makedirs(os.path.join(d, "tools"))
    for ad in ("duzelt.py", "arama.py", "gorsel_koken.py"):
        shutil.copy2(os.path.join(kok, "tools", ad), os.path.join(d, "tools", ad))
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(_SAHTE_KATALOG, f, ensure_ascii=False, indent=2)
    return d


def duzelt_cagir(repo, argv):
    """Sahte repodaki GERCEK duzelt.py'yi cagir; (rc, urunler.json sha256) dondur."""
    p = subprocess.run([sys.executable, os.path.join(repo, "tools", "duzelt.py")] + argv,
                       capture_output=True, text=True)
    with open(os.path.join(repo, "urunler.json"), "rb") as f:
        return p.returncode, hashlib.sha256(f.read()).hexdigest(), (p.stdout + p.stderr)


def _kayit(repo, uid):
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        for u in json.load(f):
            if u.get("id") == uid:
                return u
    return {}


def kabul(kok):
    arama = yukle(kok, "arama", "arama.py")
    d1 = yukle(kok, "d1sync", "d1-sync.py")
    with open(os.path.join(kok, "tools", "d1-sema.sql"), encoding="utf-8") as f:
        sema_metni = f.read()
    sema = sema_kolonlari(sema_metni, "urunler")
    goc = dict(d1.GOC_KOLON)
    kt = sema_kolonlari(d1._KT_SEMA, "urunler")

    # ══ A EKSENI — VERI (gercek katalog) ═══════════════════════════════════════════
    print("\n[A] VERI — urunler.json (kategori, altkategori) tutarliligi")
    with open(os.path.join(GERCEK_KOK, "urunler.json"), encoding="utf-8") as f:
        katalog = json.load(f)
    dolu, bos, ihlal = 0, 0, []
    for u in katalog:
        if not isinstance(u, dict):
            continue
        ham = u.get("altkategori")
        if isinstance(ham, str) and ham.strip():
            dolu += 1
        else:
            bos += 1
        sebep = arama.altkategori_sebebi(u.get("kategori"), ham)
        if sebep:
            ihlal.append((u.get("id"), u.get("kategori"), ham, sebep))
    dogrula("A1 hicbir kayitta izinsiz/tutarsiz altkategori YOK", not ihlal,
            "; ".join("%s: %s" % (i[0], i[3]) for i in ihlal[:5]))
    dogrula("A2 BOS/eksik altkategori GECERLI sayiliyor (alan opsiyonel — yanlis-pozitif "
            "tum katalogu bloklamaz)",
            arama.altkategori_sebebi("Marin", "") is None
            and arama.altkategori_sebebi("Ev", None) is None
            and arama.altkategori_sebebi("Boyle Bir Kategori Yok", None) is None)
    esles = {}
    for u in katalog:
        if isinstance(u, dict) and isinstance(u.get("altkategori"), str) \
                and u["altkategori"].strip():
            esles.setdefault(u.get("kategori"), set()).add(u["altkategori"])
    dogrula("A3 katalogta FIILEN kullanilan her esles izinli kumede TANIMLI "
            "(izinli kume katalogtan turedi, tersi degil)",
            all(v <= set(arama.ALTKATEGORI_IZINLI.get(k, ())) for k, v in esles.items()),
            {k: sorted(v) for k, v in esles.items()})
    # 🔴 KATALOG <-> D1 METIN AYRISMASI: kataloga YAZILAN metin ile D1'e GIDEN metin
    # birebir ayni olmali. Ayrisirsa site ile Ege ayni urunu FARKLI yazimla gorur ve
    # hicbir hash/senkron ekseni bunu yakalamaz (olculdu 1 Agu: ' Elektrik' kapidan rc=0
    # geciyordu, katalog ' Elektrik' D1 'Elektrik' oluyordu).
    ayrisan = [(u.get("id"), u.get("altkategori"), arama.altkategori_kanonik(u))
               for u in katalog
               if isinstance(u, dict)
               and arama.altkategori_sebebi(u.get("kategori"), u.get("altkategori")) is None
               and arama.altkategori_kanonik(u)
               != (u.get("altkategori") if isinstance(u.get("altkategori"), str) else "")]
    dogrula("A4 KABUL EDILEN her kayitta katalog metni == D1 metni (urunler.json ile D1 "
            "SESSIZCE ayrisamaz)", not ayrisan, ayrisan[:5])
    print("  OLCUM: %d kayit · altkategori dolu %d · bos/eksik %d · esles %d · tekil deger %d"
          " · katalog!=D1 ayrisan %d"
          % (len(katalog), dolu, bos, sum(len(v) for v in esles.values()),
             len({x for v in esles.values() for x in v}), len(ayrisan)))

    # ══ B EKSENI — TEDARIKCI IMZASI (depo PUBLIC) ══════════════════════════════════
    print("\n[B] IMZA — deger tedarikci kimligi ele vermesin")
    tekil = sorted({x for v in esles.values() for x in v})
    supheli = [(d, arama.altkategori_imza_sebebi(d)) for d in tekil
               if arama.altkategori_imza_sebebi(d)]
    dogrula("B1 katalogtaki her tekil altkategori degeri imza nobetinden GECIYOR "
            "(jenerik Turkce kategori adi)", not supheli, supheli)
    izinli_hepsi = [d for v in arama.ALTKATEGORI_IZINLI.values() for d in v]
    izinli_supheli = [(d, arama.altkategori_imza_sebebi(d)) for d in izinli_hepsi
                      if arama.altkategori_imza_sebebi(d)]
    dogrula("B2 IZINLI kumesinin KENDISI de imza nobetinden geciyor (mimarin elle girisi "
            "denetimsiz kalmaz)", not izinli_supheli, izinli_supheli)
    markalar = set()
    for u in katalog:
        if isinstance(u, dict):
            for m in (u.get("marka") or []):
                if isinstance(m, str) and m.strip():
                    markalar.add(m.strip().lower())
    carpisan = []
    for d in tekil + izinli_hepsi:
        for w in d.replace("-", " ").replace("/", " ").split():
            if w.lower() in markalar:
                carpisan.append((d, w))
    dogrula("B3 hicbir altkategori jetonu katalogun MARKA adlariyla carpismiyor "
            "(marka/firma adi sizmasi)", not carpisan, carpisan[:5])
    _imza_fikstur = [
        ("Tekne Boyasi 2K", "rakam"),
        ("tedarikci-vitrini.com", "alan adi"),
        ("SKU Boya", "TAMAMI BUYUK jeton"),
        ("Boya & Bakım", "izinsiz karakter"),
        ("Marka® Boya", "ticari isaret"),
        ("Wax Polish", "Turkce disi harf (w/x)"),
        ("Boya Bakım Onarım Tamir Bakim", "cok fazla kelime"),
        ("A" * 41, "cok uzun"),
        (["dizi"], "metin degil"),
    ]
    gecen_supheli = [d for d, _ in _imza_fikstur if not arama.altkategori_imza_sebebi(d)]
    dogrula("B4 imza nobeti FIILEN reddediyor (%d supheli fikstur: rakam/alan adi/SKU/"
            "ticari isaret/yabanci harf/uzunluk/tip)" % len(_imza_fikstur),
            not gecen_supheli, gecen_supheli)
    dogrula("B5 nobet YANLIS-POZITIF uretmiyor (jenerik Turkce terimler geciyor)",
            not [d for d in ("Astar", "Yapıştırıcı", "Zehirli Boya", "Boya - Bakım",
                             "Sintine ve Ekipmanları", "Elektrik/Aydınlatma")
                 if arama.altkategori_imza_sebebi(d)],
            [d for d in ("Astar", "Yapıştırıcı", "Zehirli Boya", "Boya - Bakım",
                         "Sintine ve Ekipmanları", "Elektrik/Aydınlatma")
             if arama.altkategori_imza_sebebi(d)])
    print("  OLCUM: tekil deger %d · izinli kume degeri %d · katalog tekil marka %d"
          % (len(tekil), len(izinli_hepsi), len(markalar)))

    # ══ C EKSENI — YAZMA YOLU (duzelt.py) ══════════════════════════════════════════
    print("\n[C] YOL — duzelt.py alani YAZABILIYOR ama KOR KABUL ETMIYOR")
    duz = yukle(kok, "duzeltmod", "duzelt.py")
    dogrula("C1 'altkategori' duzelt.py DEGISTIRILEBILIR kumesinde (MaCiT alani mesru "
            "yoldan doldurabiliyor)", "altkategori" in duz.DEGISTIRILEBILIR,
            sorted(duz.DEGISTIRILEBILIR))
    dogrula("C2 bilinmeyen deger REDDEDILIYOR (sebep uretiliyor)",
            arama.altkategori_sebebi("Marin", "Uydurma Altkategori") is not None)
    dogrula("C3 YANLIS kategoriye ait deger REDDEDILIYOR (Marin degeri Ev'de gecmez)",
            arama.altkategori_sebebi("Ev", "Boya - Bakım") is not None)
    dogrula("C4 metin OLMAYAN deger REDDEDILIYOR (dizi/sozluk/sayi)",
            arama.altkategori_sebebi("Marin", ["Boya - Bakım"]) is not None
            and arama.altkategori_sebebi("Marin", 5) is not None)
    dogrula("C5 GECERLI esles KABUL EDILIYOR (kapi gereginden dar degil)",
            arama.altkategori_sebebi("Marin", "Boya - Bakım") is None
            and arama.altkategori_sebebi("Marin", "Sintine ve Ekipmanları") is None)
    # KANONIK OLMAYAN yazim (bosluk ekseni) — bu eksen ONCE FAIL-OPEN'DI: uyelik testi
    # strip() SONRASI yapildigi icin ' Elektrik' rc=0 ile kabul ediliyor, kataloga HAM,
    # D1'e KIRPILMIS gidiyordu. Simdi fail-closed.
    _bosluklu = (" Elektrik", "Elektrik ", " Elektrik ", "\tElektrik", "Elektrik\n",
                 " Pervaneler", "Pervaneler ", "   ")
    _gecen_bosluklu = [v for v in _bosluklu
                       if arama.altkategori_sebebi("Marin", v) is None]
    dogrula("C12 KANONIK OLMAYAN yazim REDDEDILIYOR (%d fikstur: bas/son bosluk, sekme, "
            "satir sonu, yalniz-bosluk) — sessizce kirpilip kabul EDILMIYOR"
            % len(_bosluklu), not _gecen_bosluklu, _gecen_bosluklu)
    _izinli12 = arama.ALTKATEGORI_IZINLI.get("Marin", ())
    _reddedilen_dogru = [d for d in _izinli12
                         if arama.altkategori_sebebi("Marin", d) is not None]
    dogrula("C13 REGRESYON: izinli kumenin %d degerinin HEPSI dogru yazimla hala KABUL "
            "(bosluk kapisi mesru veriyi kesmiyor)" % len(_izinli12),
            not _reddedilen_dogru, _reddedilen_dogru)
    _yakin = ("Elektrikk", "elektrik", "ELEKTRIK", "Pervanelerr", "pervaneler")
    _gecen_yakin = [d for d in _yakin if arama.altkategori_sebebi("Marin", d) is None]
    dogrula("C14 REGRESYON: YAKIN yazimlar hala RED (%s)" % ", ".join(_yakin),
            not _gecen_yakin, _gecen_yakin)

    repo = sahte_repo(kok)
    try:
        rc, sha_once, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "baslik",
                                              "--deger", "Isinma"])
        rc, sha0, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "altkategori",
                                          "--deger", "Uydurma Altkategori"])
        dogrula("C6 GERCEK duzelt.py: bilinmeyen deger -> rc=%d (FAIL-CLOSED) ve "
                "urunler.json BYTE-ESIT kalir" % duz.RC_ALTKATEGORI,
                rc == duz.RC_ALTKATEGORI and sha0 == sha_once, "rc=%s" % rc)
        rc, _, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "altkategori",
                                       "--deger", "Boya - Bakım"])
        dogrula("C7 GERCEK duzelt.py: GECERLI deger YAZILIYOR (yol fiilen ACIK)",
                rc == 0 and _kayit(repo, "alt-test-1").get("altkategori") == "Boya - Bakım",
                "rc=%s deger=%r" % (rc, _kayit(repo, "alt-test-1").get("altkategori")))
        _, sha1, _ = duzelt_cagir(repo, ["alt-test-2", "--alan", "baslik", "--deger", "X"])
        rc, sha2, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "kategori",
                                          "--deger", "Ev"])
        dogrula("C8 KATEGORI CEVIRME DELIGI: altkategori'ye DOKUNMADAN kategori "
                "degistirilince ikili TUTARSIZ kalamaz -> reddedilir",
                rc == duz.RC_ALTKATEGORI and sha2 == sha1, "rc=%s" % rc)
        rc, _, _ = duzelt_cagir(repo, ["alt-test-1", "--alan-sil", "altkategori"])
        dogrula("C9 alan KALDIRILABILIYOR (--alan-sil) — opsiyonel alan kilitlenmiyor",
                rc == 0 and "altkategori" not in _kayit(repo, "alt-test-1"), "rc=%s" % rc)
        rc, _, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "altkategori", "--deger", ""])
        dogrula("C10 BOS deger KABUL EDILIYOR (alan opsiyonel)",
                rc == 0 and _kayit(repo, "alt-test-1").get("altkategori") == "", "rc=%s" % rc)
        islem = os.path.join(repo, "islemler.json")
        with open(islem, "w", encoding="utf-8") as f:
            json.dump([{"id": "alt-test-1", "alan": "altkategori", "deger": "Boya - Bakım"},
                       {"id": "alt-test-2", "alan": "altkategori", "deger": "Boya - Bakım"}],
                      f, ensure_ascii=False)
        _, sha3, _ = duzelt_cagir(repo, ["alt-test-2", "--alan", "baslik", "--deger", "Y"])
        rc, sha4, _ = duzelt_cagir(repo, ["--toplu", islem])
        dogrula("C11 TOPLU kip AYNI kapidan geciyor: bir islem gecersizse HICBIRI "
                "yazilmaz (ya hep ya hic)",
                rc == duz.RC_ALTKATEGORI and sha4 == sha3, "rc=%s" % rc)
        _, sha5, _ = duzelt_cagir(repo, ["alt-test-2", "--alan", "baslik", "--deger", "Z"])
        rc_bos, sha6, _ = duzelt_cagir(repo, ["alt-test-1", "--alan", "altkategori",
                                              "--deger", " Elektrik"])
        dogrula("C15 GERCEK duzelt.py: BOSLUKLU deger -> rc=%d (FAIL-CLOSED) ve "
                "urunler.json BYTE-ESIT kalir — kataloga ham ' Elektrik' YAZILAMAZ "
                "(D1'e kirpilmis gidip ayrisamaz)" % duz.RC_ALTKATEGORI,
                rc_bos == duz.RC_ALTKATEGORI and sha6 == sha5, "rc=%s" % rc_bos)
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    # ══ D EKSENI — IKIZ TANIM + HASH KAPSAMI ═══════════════════════════════════════
    print("\n[D] IKIZ TANIM — sema / GOC_KOLON / _KT_SEMA / INSERT / KOLONLAR + hash")
    ornek = _urun("a", altkategori="Boya - Bakım")
    sql = d1.satir_sql(ornek, 1, arama.haystack(ornek), arama.urun_hash(ornek))
    ins = insert_kolonlari(sql)
    conf = conflict_kolonlari(sql)
    dogrula("D1 `altkategori` d1-sema.sql CREATE TABLE'da (temiz DB ayni semayi alir)",
            sema.get("altkategori") == "TEXT", sema.get("altkategori"))
    dogrula("D2 `altkategori` GOC_KOLON'da (canli tablo ALTER ile alir)",
            "altkategori" in goc, sorted(goc))
    dogrula("D3 `altkategori` _KT_SEMA'da (offline fikstur canli semadan AYRISMAZ)",
            kt.get("altkategori") == "TEXT", kt.get("altkategori"))
    dogrula("D4 `altkategori` satir_sql INSERT listesinde (canlida 'no such column' yok)",
            "altkategori" in ins, ins)
    dogrula("D5 `altkategori` KOLONLAR'da (ON CONFLICT yolunda da GUNCELLENIR — mevcut "
            "satirda alt-filtre bayat kalmaz)", "altkategori" in d1.KOLONLAR, d1.KOLONLAR)
    dogrula("D6 `altkategori` BES tanimin HEPSINDE (biri eksikse yol yarim acilmis olur)",
            all(("altkategori" in x) for x in (sema, goc, kt, ins, d1.KOLONLAR)),
            (("altkategori" in sema), ("altkategori" in goc), ("altkategori" in kt),
             ("altkategori" in ins), ("altkategori" in d1.KOLONLAR)))
    fark = [k for k in ins if k not in d1.KOLONLAR]
    dogrula("D7 INSERT − KOLONLAR == KASITLI_DISARIDA (yeni kolon sessizce upsert DISI "
            "kalamaz)", sorted(fark) == sorted(d1.KASITLI_DISARIDA),
            "fark=%s kasitli=%s" % (sorted(fark), sorted(d1.KASITLI_DISARIDA)))
    dogrula("D8 ON CONFLICT SET listesi == KOLONLAR (uretilen SQL sabitle ayrismiyor)",
            sorted(conf) == sorted(d1.KOLONLAR), sorted(conf))

    h_yok = arama.urun_hash(_urun("a"))
    h_bos = arama.urun_hash(_urun("a", altkategori=""))
    h_boya = arama.urun_hash(_urun("a", altkategori="Boya - Bakım"))
    h_sintine = arama.urun_hash(_urun("a", altkategori="Sintine ve Ekipmanları"))
    dogrula("D9 HASH KAPSAMI: altkategori degisince urun_hash DEGISIR (yoksa diff-upsert "
            "satiri 'degismemis' sayar ve D1'e HIC yazmaz -> alt-filtre sessizce bayat)",
            len({h_yok, h_boya, h_sintine}) == 3,
            "yok=%s boya=%s sintine=%s" % (h_yok[:8], h_boya[:8], h_sintine[:8]))
    dogrula("D10 alan YOK ile BOS ayni hash'i verir (bos = alan yok; gereksiz yeniden "
            "yazim uretmez)", h_yok == h_bos)
    h_izinsiz = arama.urun_hash(_urun("a", altkategori="Uydurma Altkategori"))
    h_yanlis_kat = arama.urun_hash(_urun("a", kategori="Ev", altkategori="Boya - Bakım"))
    dogrula("D11 FAIL-CLOSED kanonik: izinsiz deger D1'e '' olarak gider (pre-push hook "
            "d1-sync'i CI kapisindan ONCE kosar -> sizan deger Ege'ye ULASAMAZ)",
            arama.altkategori_kanonik(_urun("a", altkategori="Uydurma Altkategori")) == ""
            and h_izinsiz == h_yok)
    dogrula("D12 FAIL-CLOSED kanonik: YANLIS kategoriye ait deger de '' olur",
            arama.altkategori_kanonik(
                _urun("a", kategori="Ev", altkategori="Boya - Bakım")) == ""
            and h_yanlis_kat == arama.urun_hash(_urun("a", kategori="Ev")))
    dogrula("D13 GECERLI deger kanoniklestirmeden GECER (kapi veriyi yutmuyor)",
            arama.altkategori_kanonik(_urun("a", altkategori="Boya - Bakım"))
            == "Boya - Bakım")
    # 🔴 TEK KAYNAK INVARYANTI (ikiz tanim yasagi, DAVRANISLA olculur): her ham deger icin
    # ya sebebi() REDDEDER (kanonik "" olur, katalog o degeri hic ALMAZ) ya da kanonik()
    # girdiyi AYNEN dondurur. Ucuncu bir hal — "kabul edildi ama D1'e baska metin gitti" —
    # katalog ile D1'in sessizce ayrismasidir; olculen kusur tam olarak buydu.
    _ham_fikstur = [
        "Elektrik", " Elektrik", "Elektrik ", " Elektrik ", "\tElektrik", "Elektrik\n",
        "Pervaneler", " Pervaneler", "Pervaneler ", "  Boya - Bakım", "Boya - Bakım",
        "Sintine ve Ekipmanları ", "", "   ", "Uydurma Altkategori", " Uydurma",
        "Elektrikk", "elektrik", "Tekne Boyasi 2K",
    ]
    _ayrisan = []
    for _v in _ham_fikstur:
        _u = _urun("a", altkategori=_v)
        _kan = arama.altkategori_kanonik(_u)
        if arama.altkategori_sebebi("Marin", _v) is None:
            if _kan != _v:
                _ayrisan.append(("KABUL ama ayrisma", _v, _kan))
        elif _kan != "":
            _ayrisan.append(("RED ama kanonik bos degil", _v, _kan))
    dogrula("D17 TEK KAYNAK: %d ham fiksturun hicbirinde 'kabul edildi ama D1 metni FARKLI' "
            "hali YOK — katalog metni ile D1 metni ayni fonksiyondan (altkategori_metin) "
            "turer" % len(_ham_fikstur), not _ayrisan, _ayrisan[:5])
    dogrula("D18 altkategori_metin TEK KAYNAK olarak MEVCUT ve kanonik bicimi uretiyor "
            "(sebebi/kanonik ikizini besleyen fonksiyon)",
            hasattr(arama, "altkategori_metin")
            and arama.altkategori_metin(" Elektrik ") == "Elektrik"
            and arama.altkategori_metin(None) == ""
            and arama.altkategori_metin(["x"]) == "",
            getattr(arama, "altkategori_metin", None))

    # SQL'i GERCEKTEN kostur: kolon listesi ile deger listesi HIZALI mi (siralama kaymasi
    # sessizdir — altkategori metni baska bir kolona, o kolonun degeri altkategori'ye duser).
    conn = sqlite3.connect(":memory:")
    conn.executescript(d1._KT_SEMA)
    conn.executescript(sql)
    satir = conn.execute("SELECT altkategori, kategori, baslik, yayinda FROM urunler "
                         "WHERE id='a'").fetchone()
    conn.close()
    dogrula("D14 uretilen INSERT sqlite'ta KOSUYOR ve altkategori DOGRU hucreye yaziliyor "
            "(kolon/deger siralama kaymasi yok)",
            satir is not None and satir[0] == "Boya - Bakım" and satir[1] == "Marin"
            and satir[3] == 0, satir)

    # diff_plan: altkategori degisimi FIILEN bir yazma uretiyor mu?
    onceki = _urun("a", altkategori="Boya - Bakım")
    sonraki = _urun("a", altkategori="Sintine ve Ekipmanları")
    # diff_plan doner: (yeni, degisen, baski_guncelle, silinen, gorulen) — id D1'de ZATEN
    # var oldugu icin yazma `degisen` kolunda beklenir.
    _yeni, degisen, _b, _s, _g = d1.diff_plan(
        [sonraki], {"a": (arama.urun_hash(onceki), "")}, {}, False, 1, {"a": 1})
    dogrula("D15 diff_plan: YALNIZ altkategori degisen urun icin upsert uretiliyor "
            "(uctan uca: alan -> hash -> yazma)",
            len(degisen) == 1 and "altkategori=excluded.altkategori" in degisen[0]
            and "Sintine ve Ekipmanları" in degisen[0], str(degisen)[:200])
    _y2, degisen2, _b2, _s2, _g2 = d1.diff_plan(
        [onceki], {"a": (arama.urun_hash(onceki), "")}, {}, False, 1, {"a": 1})
    dogrula("D16 diff_plan YANLIS-POZITIF uretmiyor: degismeyen urun icin yazma YOK "
            "(altkategori tum katalogu her push'ta yeniden yazdirmiyor)",
            not degisen2, str(degisen2)[:200])

    print("\nSONUC: %s — gecen %d · kalan %d"
          % ("YESIL" if kalan[0] == 0 else "KIRMIZI", gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


# ── CIFT YONLU MUTASYON ─────────────────────────────────────────────────────────────
# KIRMIZI beklenen = oldurucu mutant (kapi yakalamali) · YESIL beklenen = ILGISIZ
# degisiklik (kapinin gereginden genis olmadiginin kaniti — yanlis-pozitif herkesin
# push'unu kirar).
#
# 🔴 CAPA BICIMI — DUZ METIN YA DA re.Pattern:
# Duz metin capa, capaladigi satirin KOMSULUGU degisince BAYATLAR ve o mutantin olctugu
# eksen SESSIZCE olculmez olur. OLCULDU (1 Agu): C1 ekseninin capasi '"konfigur",
# "altkategori"}' idi; commit 026baebc DEGISTIRILEBILIR kumesine "tur", "gorselsiz"
# ekleyince kume literalinin SONU kaydi, capa 0 kez eslesti ve C1'in oldurucu gucu bir
# tur boyunca OLCULMEDI. Cozum iki katli:
#   1) Kirilgan capalar re.Pattern'e cevrildi — capa artik komsu satirlara DEGIL, mutasyona
#      ugrayacak YAPIYA (ornegin DEGISTIRILEBILIR literalinin ICI) bakiyor.
#   2) Capa kayarsa tur KIRMIZI yanar ve mutant SAYILMAZ (asagida _mutasyon_uygula +
#      "mutant fiilen uygulandi mi" sha kontrolu). "Capa bulunamadi" ASLA yesil degildir.
# re.Pattern kullanildiginda `yeni` bir m.expand() sablonudur (\1 gruplari gecerlidir).
MUTANTLAR = [
    ("arama.py", "        altkategori_kanonik(u),\n", "", "KIRMIZI",
     "D9: altkategori hash'ten cikar -> alt-filtre degisimi D1'e HIC yazilmaz"),
    # 🔴 CAPA ONARIMI (2 Agu 2. tur) — asagidaki 4 capa `uyum` ekseni d1-sync.py'ye
    # eklenince BAYATLAMISTI (0 kez eslesti) ve olctukleri eksenler bir tur boyunca
    # OLCULMEMISTI: KOLONLAR literalinin sonuna "uyum" geldi, INSERT kolon listesi
    # "altkategori,uyum,yayinda" oldu, offline fikstur semasinda altkategori satiri
    # virgul aldi. Ders [[ikiz-tanim-sessiz-ayrisma]] + bu dosyanin ustundeki CAPA BICIMI
    # notu: kirilgan duz-metin capalar re.Pattern'e cevrildi — capa artik KOMSU jetona
    # degil, mutasyona ugrayacak YAPIYA bakiyor, komsulugu bir daha degisirse de eslesir.
    ("d1-sync.py", re.compile(r'\n    "altkategori",\n'), "\n", "KIRMIZI",
     "D5/D7: KOLONLAR disi kalir -> mevcut satirda altkategori ESKI degerde donar"),
    ("d1-sync.py", re.compile(r'"altkategori,((?:\w+,)*)yayinda\) VALUES \("'),
     r'"\1yayinda) VALUES ("', "KIRMIZI",
     "D4: INSERT listesinden duser -> canlida kolon HIC yazilmaz"),
    ("d1-sync.py", re.compile(r'"altkategori,((?:\w+,)*)yayinda\) VALUES \("'),
     r'"\1yayinda,altkategori) VALUES ("',
     "KIRMIZI", "D14: kolon/deger siralama kaymasi (deger yanlis hucreye duser)"),
    ("d1-sync.py", '    ("altkategori", "TEXT NOT NULL DEFAULT \'\'"),\n', "", "KIRMIZI",
     "D2: canli tablo ALTER'i kaybolur -> mevcut D1'de kolon HIC olusmaz"),
    ("d1-sync.py", re.compile(r"\n  altkategori TEXT NOT NULL DEFAULT ''(,?)\n"), "\n",
     "KIRMIZI",
     "D3: offline fikstur semasi canli semadan AYRISIR (ikiz tanim drift'i)"),
    ("d1-sema.sql", "  altkategori TEXT NOT NULL DEFAULT '',\n", "", "KIRMIZI",
     "D1: temiz DB kolonsuz kurulur (testler yesil, canli baska sema)"),
    ("arama.py", "    if altkategori_sebebi(u.get(\"kategori\"), deger) is not None:\n"
                 "        return \"\"\n", "", "KIRMIZI",
     "D11/D12: kanonik FAIL-OPEN olur -> izinsiz/sizdiran deger D1'e ham gider"),
    ("arama.py", "    if not isinstance(deger, str):\n"
                 "        return \"metin degil (%s)\" % type(deger).__name__\n",
     "    if not isinstance(deger, str):\n        return None\n", "KIRMIZI",
     "B4: imza nobeti tip ekseninde fail-open olur"),
    # 🔴 BURADA BIR ESDEGER MUTANT OLCULDU (1 Agu) ve BILEREK LISTEDE DEGIL:
    # `if c.isdigit(): return "rakam iceriyor..."` dalini SILMEK kapiyi KIRMIZI YAKMAZ —
    # rakam zaten _ALTKAT_HARF/_ALTKAT_AYIRAC beyaz listesinde OLMADIGI icin bir alt
    # satirdaki "izinsiz karakter" dalina duser ve REDDEDILIR. Yani o dal davranisi
    # DEGISTIRMEZ, yalnizca hata MESAJINI netlestirir. Esdeger mutant "kapi zayif"
    # demek DEGILDIR; listeye konsaydi kalici yalanci-basarisizlik uretirdi.
    # Rakam ekseninin GERCEK oldurucu mutanti asagidaki: beyaz listeyi genisletmek.
    ("arama.py", '_ALTKAT_AYIRAC = set(" -/")', '_ALTKAT_AYIRAC = set(" -/0123456789")',
     "KIRMIZI", "B4: rakam beyaz listeye girer -> urun kodu/SKU tasiyan deger GECER"),
    ("arama.py", "    if d not in izinli:", "    if False:", "KIRMIZI",
     "A1/C2: izinli kume kalkar -> uydurma taksonomi sessizce kabul edilir"),
    ("arama.py", re.compile(r"    if d != deger:\n        return \(\"KANONIK DEGIL.*?\)\n",
                            re.S), "", "KIRMIZI",
     "A4/C12/C15/D17: kanonik yazim kapisi FAIL-OPEN olur -> ' Elektrik' kabul edilir, "
     "kataloga HAM, D1'e KIRPILMIS gider (katalog<->D1 sessiz metin ayrismasi)"),
    # 🔴 CAPA re.Pattern: DEGISTIRILEBILIR bir KUME LITERALI ve icerigi buyuyor (026baebc
    # "tur"/"gorselsiz" ekledi). Capa literalin SINIRINA degil ICINDEKI jetona bakiyor;
    # kume bir daha buyudugunde/kuculdugunde de eslesir.
    ("duzelt.py", re.compile(r'(DEGISTIRILEBILIR = \{[^}]*?)"altkategori",\s*'), r"\1",
     "KIRMIZI", "C1: alan yeniden YAZILAMAZ olur (bugunku tikanma geri gelir)"),
    ("duzelt.py", re.compile(
        r"( +)alt_ihlal = _altkategori_ihlalleri\(urunler, \{args\.id\}\)"),
     r"\1alt_ihlal = []", "KIRMIZI",
     "C6/C8: tek-urun kipinde kapi devre disi -> kor kabul"),
    ("duzelt.py", re.compile(
        r"( +)urunler, set\(setler\) \| set\(alan_silmeler\)\)"),
     r"\1urunler, set())", "KIRMIZI",
     "C11: TOPLU kipte kapi devre disi (tek-urun kipi dogru olsa BILE)"),
    ("d1-sync.py", "TAM_OKUMA_ESIGI = 800", "TAM_OKUMA_ESIGI = 900", "YESIL",
     "ILGISIZ: geri-okuma olcek esigi — altkategori iddialarina DOKUNMAZ"),
    ("d1-sema.sql", "-- Kurulum: python3 tools/d1-sync.py --sema",
     "-- Kurulum: python3 tools/d1-sync.py --sema   (ilgisiz yorum)", "YESIL",
     "ILGISIZ: sema dosyasinda yorum — kapi metne DEGIL yapiya bakiyor"),
]

# d1-sync.py konfigur-bundle-kapisi.py'yi, duzelt.py gorsel_koken.py'yi ve arama.py'yi
# KOSULSUZ yukler -> hepsi kopyaya girmeli. 🔴 EKSIK KOPYA SESSIZ DEGIL AMA ALDATICIDIR:
# eksikte kapi COKER, rc!=0 doner ve mutasyon harness'i bunu "KIRMIZI = mutant olduruldu"
# sanar; 14 oldurucu mutantin hepsi ayni sebeple yalanci-KIRMIZI olur (olculdu, 1 Agu:
# konfigur-bundle-kapisi.py eksikti, 16 mutantin 16'si "0 iddia kirmizi" ile duştu).
# MUTASYONSUZ KONTROL bu yuzden mutasyon() icinde ZORUNLU on-kosuldur (asagida M00).
KOPYALANAN = ["arama.py", "d1-sync.py", "d1-sema.sql", "duzelt.py", "gorsel_koken.py",
              "konfigur-bundle-kapisi.py"]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kopya_kur():
    """KOPYALANAN dosyalari yeni bir gecici agaca kur; urunler.json (14 MB) SYMLINK."""
    tmp = tempfile.mkdtemp(prefix="pruvo-altkat-mut-")
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(GERCEK_KOK, "tools", ad), os.path.join(tmp, "tools", ad))
    os.symlink(os.path.join(GERCEK_KOK, "urunler.json"), os.path.join(tmp, "urunler.json"))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def _mutasyon_uygula(metin, eski, yeni):
    """(yeni_metin, eslesme_sayisi). eski: duz metin ya da re.Pattern (yeni = expand sablonu).

    eslesme_sayisi != 1 ise yeni_metin None doner — cagiran bunu HATA sayar (yesil DEGIL).
    """
    if isinstance(eski, re.Pattern):
        esler = list(eski.finditer(metin))
        if len(esler) != 1:
            return None, len(esler)
        m = esler[0]
        return metin[:m.start()] + m.expand(yeni) + metin[m.end():], 1
    sayi = metin.count(eski)
    if sayi != 1:
        return None, sayi
    return metin.replace(eski, yeni), 1


def _capa_metni(eski):
    return eski.pattern if isinstance(eski, re.Pattern) else eski


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    basarisiz = []

    # ── M00 MUTASYONSUZ KONTROL (ZORUNLU ON-KOSUL) ────────────────────────────────
    # Kopya agaci MUTASYONSUZ halde YESIL vermezse harness BOZUKTUR ve butun "KIRMIZI"
    # sonuclari yalancidir (mutant degil, cokme olculur). Bu satir olculmus bir vakadan
    # dogdu (1 Agu): eksik bir kopya dosyasi yuzunden 14 oldurucu mutantin hepsi ayni
    # ImportError ile "olduruldu" gorunuyordu. Kontrol KIRMIZIYSA olcum DURUR.
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    kontrol_ok = p0.returncode == 0
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s (harness saglam mi)"
          % ("OK  " if kontrol_ok else "HATA", "YESIL" if kontrol_ok else "KIRMIZI"))
    if not kontrol_ok:
        print("     " + (p0.stderr or p0.stdout).strip().splitlines()[-1][:200])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk, mutant sonuclari YALANCI.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)
    uygulanan = 0
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = _kopya_kur()
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        # 🔴 CAPA KAYMASI = KIRMIZI, "gecti" DEGIL. Capa eslesmezse o eksen OLCULMEMISTIR;
        # sessizce atlanirsa tur "16/16 tuttu" der ve olculmeyen eksen olculmus sanilir.
        mutant, sayi = _mutasyon_uygula(metin, eski, yeni)
        if mutant is None:
            basarisiz.append("M%02d CAPA BAYAT (%d kez eslesti, 1 olmali) %s: %s"
                             % (i, sayi, dosya, _capa_metni(eski)[:70]))
            print("  HATA M%02d [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        # Capa eslesti ama metin DEGISMEDIYSE mutant fiilen uygulanmamistir (eski == yeni,
        # ya da expand sablonu ayni metni uretti). Bu da OLCULEMEDI'dir, yesil DEGIL.
        if mutant == metin:
            basarisiz.append("M%02d MUTANT UYGULANMADI (metin DEGISMEDI) %s: %s"
                             % (i, dosya, _capa_metni(eski)[:70]))
            print("  HATA M%02d [%s] %s -> MUTANT UYGULANMADI | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(mutant)
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        isaret = "OK  " if goruldu == beklenen else "HATA"
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir (import
        # hatasi, sozdizimi). O "olduruldu" DEGIL "olculemedi"dir. En az bir ADLANDIRILMIS
        # iddianin KALDI demesi sarti bu ayrimi makineye tasir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("M%02d %s: KIRMIZI ama HICBIR iddia KALDI demedi — mutant "
                             "oldurulmedi, kapi COKTU (yalanci kanit)" % (i, dosya))
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
    # Her uygulanmayan mutant zaten dongude basarisiz'a yazildi (CAPA BAYAT / UYGULANMADI);
    # bu satir sayiyi TEK BAKISTA gorunur kilar.
    print("  MUTANT FIILEN UYGULANDI: %d/%d (capasi bayat olan mutant OLCULMEMIS sayilir)"
          % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK,
                    help="modulleri/semayi bu agactan oku (mutasyon kopyasi)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon olcumu (elle; canli dosyaya DOKUNMAZ)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== ALT KATEGORI KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())
