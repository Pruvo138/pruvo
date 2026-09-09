#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — ana sayfa KATEGORI PANEL BASLIGINDAKI URUN SAYISI ("MARIN 1901 urun").

  python3 tools/kat-sayisi-test.py              # kabul (CI'da bloklayici)
  python3 tools/kat-sayisi-test.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/kat-sayisi-test.py --kok /yol   # BASKA agactan oku (mutasyon icin)

NEDEN VAR (Okan'in DOGRUDAN istegi, 9 Eyl 2026): panel basliklarinda kategorinin urun
sayisi gorunsun. Istegin ASIL sarti sayinin GORUNMESI degil, HARDCODE OLMAMASIDIR —
katalog buyudukce sayi kendiliginden yukselmeli. Bir sabit yazilsaydi bugun DOGRU
gorunur, ilk urun partisinden sonra SESSIZCE yalan soylerdi; hicbir gorsel kontrol bunu
yakalamaz. Bu kapinin varlik sebebi o sessiz yalandir.

OLCULEN / KAPATILAN SESSIZ-HATA SINIFLARI:
  1. HARDCODE — sayi katalogdan turemiyor. D5 (uretici: urun eklenince sayi TAM o kadar
     artar) ve D16 (istemci: indeksteki sayi degisince BASILAN sayi da degisir) olcer.
     Ikisi ayri katmandadir; biri tek basina otekini kanitlamaz.
  2. MUKERRER SAYIM — sayi marka/uyum eksenli bir tablodan turetilirse cok markali urun
     birden fazla sayilir. D2/D3 olcer; M06 mutanti tam bu yolu acar.
  3. FAIL-OPEN — indeks/alan/deger yokken istemci COKER ya da bozuk deger BASAR ve panel
     komple kaybolur. D13/D14/D15 olcer (M01/M02 oldurucu).
  4. GORUNMEZ SOZLESME KIRILMASI — indekse alan eklerken mevcut tuketicilerin okudugu
     `surum`/`alt`/`kat`/`katalt` anlamca kayar. D6/D7/D8 olcer.
  5. CSS KANCASININ KOPMASI — sayi basilir ama kendi sinifini almaz; o zaman basligin
     clamp(26px,6vw,46px) puntosuyla cizilir ve mobilde basligi kirar. D11 olcer (M05).

MIMARI: hukum burada, ISTEMCI ICRASI tools/kat-sayisi-kosum.js'te (index.html'in GERCEK
inline scripti node:vm'de kosar; kod KOPYALANMAZ). Kosum dosyasi bilerek "-test.js"
ADINDA DEGIL: tools/ci-kapsam-test.py kesfi ikinci bir CI girisi beklemesin.

INDEKS UYDURULMAZ: GERCEK uretec (tools/cip-indeks.py) hem sentetik fikstur hem GERCEK
katalog uzerinde calistirilir, ciktisi kosuma verilir. Ureticide ya da istemcide bir
mutasyon otekini de kirmizi yakar (tek olcum, iki taraf).

GORUNUR KUME: uretece `gizli` kayitlari DUSURULMUS liste verilir — build.py:143 ile AYNI
suzgec, ikinci bir tanim YAZILMAZ (olculdu 9 Eyl: 36.153 kayit, 958 gizli, 35.195
gorunur; Marin ham 2.855 / gorunur 1.901 — musterinin gordugu sayi 1.901'dir).

AGA CIKMAZ, DISKE YAZMAZ: kosumun fetch'i asla cevap vermez; index.html / urunler.json
yalnizca OKUNUR. Mutant HER ZAMAN gecici bir KOPYAYA yazilir, canli dosyaya ASLA
(sha256 butunlugu batarya sonunda olculur).
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)

# 🔴 IDDIA SAYISI SOZLESMESI (olcut ESIT, ">=" DEGIL): bir iddia SESSIZCE dusurulurse
# ya da bir kol hic kosmazsa kapi KIRMIZI yanar ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
BEKLENEN_IDDIA = 16

# En az bu kadar panel basliginda sayi GORUNMELI (Okan'in kabul olcutu "uc kategori").
# SAYI DEGIL AD civilenemez cunku panel kumesi esikten (KAT_PANEL_MIN_CIP) turer; taban
# 9 Eyl'de OLCULDU: 7 panel. Esik 3'tur ve TABAN DEGIL ALT SINIRDIR.
EN_AZ_SAYILI_BASLIK = 3

BASLIK_DESENI = re.compile(r"^(.+?) (\d+) ürün$")


# ---------------------------------------------------------------- iddia defteri
class Defter(object):
    def __init__(self):
        self.gecen = 0
        self.kalan = []

    def __call__(self, ad, kosul, detay=""):
        if kosul:
            self.gecen += 1
            print("  OK    %s%s" % (ad, (" | " + str(detay)) if detay else ""))
        else:
            self.kalan.append(ad)
            print("  KALDI %s | %s" % (ad, detay))

    @property
    def toplam(self):
        return self.gecen + len(self.kalan)


# ---------------------------------------------------------------- yardimcilar
def _uretec_yukle(kok):
    """<kok>/tools/cip-indeks.py'yi BENZERSIZ modul adiyla yukler (mutant kopyasi da olabilir).

    🔴 Modul kendi dizinini `sys.path`e ITER; bu yuzden kopya agactaki uretec kendi
    KOPYA kardeslerini (marka_model_build vb.) gorur — PYTHONPATH numarasi GEREKMEZ ve
    calismazdi da ([[pythonpath-mutanti-modulun-kendi-syspath-insertiyle-olur]])."""
    yol = os.path.join(kok, "tools", "cip-indeks.py")
    ad = "cip_indeks_%s" % hashlib.sha256(yol.encode("utf-8")).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gorunur(kok):
    """build.py:143 ile AYNI suzgec — ikinci bir `gizli` tanimi yazilmaz."""
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        return [p for p in json.load(f) if not p.get("gizli")]


def _kosum(kok, indeks_yolu, index_html=None):
    """Istemci kosumu: index.html'in GERCEK scriptini node:vm'de calistirip DOM'u doner."""
    cmd = [_node(), os.path.join(kok, "tools", "kat-sayisi-kosum.js"),
           "--kok", kok, "--indeks", indeks_yolu]
    if index_html:
        cmd += ["--index-html", index_html]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return {"_cokme": (p.stderr or p.stdout or "").strip()[-500:],
                "hata": None, "konsolHatalari": [], "panelSayisi": 0, "basliklar": []}
    return json.loads(p.stdout)


def _node():
    return shutil.which("node") or "node"


def _yaz(dizin, ad, veri):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    return yol


# ---------------------------------------------------------------- fikstur
# SENTETIK KATALOG — uretici kolunu ANINDA ve DETERMINISTIK olcer (gercek katalog 35k
# kayit / ~6 s; buyume iddiasi orada olculemezdi cunku urun EKLEYEMEYIZ).
# Kategori adlari GERCEKTIR (index.html CATEGORIES) — uydurma kategori sayilmaz.
# 🔴 MARKA EKSENI BILEREK PURUZLU VE DENGESIZ: bir kayit IKI markali, UC kayit MARKASIZ.
# Sayim URUN bazli oldugu icin bu, dogru govdenin sonucunu ETKILEMEZ; ama sayim marka
# bazli bir tabloya kaydirilirsa (M05) cok markali kayit iki kez, markasiz kayit HIC
# sayilir ve fikstur bunu ANINDA gorur.
# 🔴 DENGE BILEREK BOZUK (OLCULDU, 9 Eyl): ilk denemede 1 cok-markali + 1 markasiz kayit
# vardi ve mutant fiksturde ESDEGER cikti — +1 ile -1 BIRBIRINI GOTURUYORDU, mutanti
# yalniz gercek katalog kolu (D9) oldurebiliyordu. Sayilar simdi kategori basina
# ayrisiyor (Marin 8 vs 7 · Otomobil 4 vs 3)
# ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
def _fikstur():
    urunler = []
    plan = [("Marin", "Pervaneler", 5), ("Otomobil", "İç Aksam", 4),
            ("Marin", "Bağlantı", 3), ("Bisiklet", "Aksesuar", 2)]
    i = 0
    for kat, altk, adet in plan:
        for _ in range(adet):
            i += 1
            if i == 1:
                marka = ["Yamaha", "Mercury"]      # COK MARKALI (marka bazli sayimda 2)
            elif i in (2, 5, 6):
                marka = []                          # MARKASIZ (marka bazli sayimda 0)
            else:
                marka = ["Yamaha"]
            urunler.append({
                "id": "fx%03d" % i, "baslik": "Fikstur %d" % i,
                "kategori": kat, "altkategori": altk,
                "marka": marka, "uyum": [], "gorseller": ["x.webp"],
                "fiyat": "100 TL", "aciklama": "fikstur",
            })
    return urunler


# ---------------------------------------------------------------- kabul
def kabul(kok):
    d = Defter()
    ci = _uretec_yukle(kok)
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_metni = f.read()
    tmp = tempfile.mkdtemp(prefix="pruvo-kat-sayisi-")
    try:
        # ============================= A) URETICI (sentetik fikstur) =============
        fx = _fikstur()
        ixf = ci.indeks_uret(fx, index_metni)

        d("D1  `katSayisi` alani VAR ve sozluk",
          isinstance(ixf.get("katSayisi"), dict),
          "tip=%s" % type(ixf.get("katSayisi")).__name__)

        beklenen = dict(collections.Counter(p["kategori"] for p in fx))
        d("D2  fikstur: katSayisi == BAGIMSIZ kategori sayimi (TAM esitlik)",
          dict(ixf.get("katSayisi") or {}) == beklenen,
          "uretec=%s beklenen=%s" % (dict(ixf.get("katSayisi") or {}), beklenen))

        d("D3  fikstur: katSayisi TOPLAMI == kayit sayisi (mukerrer/eksik yok)",
          sum((ixf.get("katSayisi") or {}).values()) == len(fx),
          "toplam=%d kayit=%d" % (sum((ixf.get("katSayisi") or {}).values()), len(fx)))

        d("D4  fikstur: anahtar kumesi == katalogdaki DOLU kategoriler (uydurma kategori yok)",
          set((ixf.get("katSayisi") or {}).keys()) == set(p["kategori"] for p in fx),
          "anahtar=%s" % sorted((ixf.get("katSayisi") or {}).keys()))

        # D5 BUYUME — HARDCODE'un uretici tarafindaki oldurucu kolu.
        buyuk = fx + [dict(p, id="ek%d" % j) for j, p in enumerate(fx[:3])]
        ixb = ci.indeks_uret(buyuk, index_metni)
        eski, yeni = (ixf.get("katSayisi") or {}), (ixb.get("katSayisi") or {})
        d("D5  BUYUME: 3 Marin urunu eklenince SADECE Marin +3 (sayi katalogdan TURER)",
          yeni.get("Marin") == eski.get("Marin", 0) + 3
          and all(yeni.get(k) == v for k, v in eski.items() if k != "Marin"),
          "once=%s sonra=%s" % (eski, yeni))

        # ============================= B) GERIYE UYUMLULUK / SOZLESME ============
        d("D6  donen anahtar kumesi == {surum,alt,kat,katalt,katSayisi} ve surum DEGISMEDI (1)",
          set(ixf.keys()) == {"surum", "alt", "kat", "katalt", "katSayisi"}
          and ixf.get("surum") == 1,
          "anahtar=%s surum=%r" % (sorted(ixf.keys()), ixf.get("surum")))

        d("D7  tuketici alanlari SAGLAM: alt=liste · kat/katalt=sozluk · her kategoride "
          "sum(katalt[kat]) == katSayisi[kat] (ayni URUN tabanindan turer)",
          isinstance(ixf.get("alt"), list) and isinstance(ixf.get("kat"), dict)
          and isinstance(ixf.get("katalt"), dict)
          and all(sum(v.values()) == (ixf["katSayisi"] or {}).get(k)
                  for k, v in ixf["katalt"].items()),
          "katalt=%s" % {k: sum(v.values()) for k, v in ixf["katalt"].items()})

        gomulu = ci.enjekte("<head></head><body></body>", ixf)
        m = re.search(r"window\.PRUVO_CIP_INDEKS=(\{.*?\});</script>", gomulu)
        d("D8  `enjekte()` calisir, gomulu metin GECERLI JSON ve katSayisi'yi TASIR",
          bool(m) and json.loads(m.group(1)).get("katSayisi") == beklenen,
          "gomuldu=%s" % bool(m))

        # ============================= C) GERCEK KATALOG + ISTEMCI ===============
        gor = _gorunur(kok)
        ix = ci.indeks_uret(gor, index_metni)
        ks = ix.get("katSayisi") or {}

        d("D9  GERCEK katalog: katSayisi toplami == GORUNUR (gizli disi) urun sayisi",
          sum(ks.values()) == len(gor),
          "toplam=%d gorunur=%d" % (sum(ks.values()), len(gor)))

        y_var = _yaz(tmp, "ix.json", ix)
        r_var = _kosum(kok, y_var)

        basliklar = r_var.get("basliklar") or []
        cozulen, sapan = {}, []
        for b in basliklar:
            mm = BASLIK_DESENI.match(b.get("metin") or "")
            if not mm:
                continue
            ad_bekl = (b.get("adMetni") or "")
            if mm.group(1) != ad_bekl:
                sapan.append("ad kaydi: %r != %r" % (mm.group(1), ad_bekl))
                continue
            cozulen[ad_bekl] = int(mm.group(2))
        # Basliktaki AD BUYUTULMUS haldedir; uretecteki kategori adiyla `_buyut` (yani
        # index.html'in toLocaleUpperCase("tr") karsiligi) uzerinden eslestirilir.
        eslesen = {}
        for ad, n in cozulen.items():
            gercek = None
            for k in ks:
                if _buyut(k) == ad:
                    gercek = k
                    break
            if gercek is None:
                sapan.append("baslik %r hicbir kategoriye eslesmedi" % ad)
            else:
                eslesen[gercek] = n

        d("D10 indeks VARKEN en az %d baslik '<AD> <N> ürün' desenine uyar ve N == uretecin "
          "sayisi (ORNEKLEME YOK, cozulen HER baslik)" % EN_AZ_SAYILI_BASLIK,
          len(eslesen) >= EN_AZ_SAYILI_BASLIK and not sapan
          and all(ks[k] == n for k, n in eslesen.items()),
          "cozulen=%d sapan=%s ornek=%s"
          % (len(eslesen), sapan[:2],
             sorted(eslesen.items(), key=lambda t: -t[1])[:3]))

        sayili = [b for b in basliklar if b.get("sayiOgeAdedi")]
        d("D11 sayi ogesi HER baslikta TEK ve sinifi TAM `kat-panel-sayi` (CSS kancasi kopmadi)",
          len(sayili) == len(basliklar) and len(basliklar) > 0
          and all(b["sayiOgeAdedi"] == 1 for b in sayili)
          and all((b.get("sayiOgesi") or "") == " %d ürün" % eslesen.get(_kat(b, ks), -1)
                  for b in sayili if _kat(b, ks)),
          "baslik=%d sayili=%d" % (len(basliklar), len(sayili)))

        d("D12 indeks VARKEN JS hatasi YOK ve konsol hatasi YOK",
          not r_var.get("_cokme") and r_var.get("hata") is None
          and not r_var.get("konsolHatalari"),
          "hata=%r konsol=%s cokme=%r"
          % (r_var.get("hata"), r_var.get("konsolHatalari"), r_var.get("_cokme")))

        # --- FAIL-CLOSED 1: indeks HIC YOK (yayin oncesi / gomme basarisiz hal) ---
        r_yok = _kosum(kok, "YOK")
        d("D13 FAIL-CLOSED indeks YOK: baslik BUGUNKU gibi (sayi basilmaz), JS hatasi YOK, "
          "panel kumesi ve ad metinleri indeks-VARKEN ile BIREBIR ayni",
          _sayisiz_ve_ayni(r_yok, r_var),
          _fark_ozeti(r_yok, r_var))

        # --- FAIL-CLOSED 2: ESKI gomulu indeks (alan SILINMIS) + YENI istemci ---
        ix_eksik = dict(ix)
        ix_eksik.pop("katSayisi")
        r_eksik = _kosum(kok, _yaz(tmp, "ix-eksik.json", ix_eksik))
        d("D14 FAIL-CLOSED `katSayisi` ALANI SILINMIS (eski indeks + yeni istemci): sayi "
          "basilmaz, JS hatasi YOK, marka/grup panelleri AYNEN calisir",
          _sayisiz_ve_ayni(r_eksik, r_var),
          _fark_ozeti(r_eksik, r_var))

        # --- FAIL-CLOSED 3: BOZUK degerler (tip/isaret/ondalik/NaN) ---
        bozuk = dict(ix)
        bozuk["katSayisi"] = {"Marin": "1901", "Otomobil": 0, "Motosiklet": -5,
                              "Bisiklet": None, "Elektronik": 1.5, "Ev": True}
        r_bozuk = _kosum(kok, _yaz(tmp, "ix-bozuk.json", bozuk))
        d("D15 FAIL-CLOSED BOZUK deger (dizge/0/negatif/null/ondalik/bool): HICBIRI "
          "basilmaz, JS hatasi YOK",
          _sayisiz_ve_ayni(r_bozuk, r_var),
          _fark_ozeti(r_bozuk, r_var))

        # --- D16 HARDCODE'un ISTEMCI tarafindaki oldurucu kolu ---
        kaydirilmis = dict(ix)
        kaydirilmis["katSayisi"] = dict((k, v + 7) for k, v in ks.items())
        r_kay = _kosum(kok, _yaz(tmp, "ix-kaydir.json", kaydirilmis))
        kay = {}
        for b in (r_kay.get("basliklar") or []):
            mm = BASLIK_DESENI.match(b.get("metin") or "")
            if mm:
                kay[b.get("adMetni")] = int(mm.group(2))
        beklenen_kay = dict((_buyut(k), v + 7) for k, v in ks.items())
        d("D16 HARDCODE YOK (istemci): indeksteki sayi +7 kaydirilinca BASILAN sayi da "
          "+7 kayar — istemci sayiyi INDEKSTEN okur",
          len(kay) >= EN_AZ_SAYILI_BASLIK
          and all(beklenen_kay.get(ad) == n for ad, n in kay.items()),
          "basilan=%s" % sorted(kay.items(), key=lambda t: -t[1])[:3])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n  IDDIA: %d gecti / %d toplam (sozlesme %d)"
          % (d.gecen, d.toplam, BEKLENEN_IDDIA))
    if d.toplam != BEKLENEN_IDDIA:
        print("  KALDI IDDIA SAYISI SOZLESMESI: %d != %d — bir kol SESSIZCE dustu"
              % (d.toplam, BEKLENEN_IDDIA))
        return 1
    if d.kalan:
        print("\nSONUC: %d iddia KALDI -> %s" % (len(d.kalan), d.kalan))
        return 1
    print("\nSONUC: KAT SAYISI KAPISI YESIL ✔")
    return 0


def _buyut(s):
    """index.html'in `toLocaleUpperCase('tr')` karsiligi (noktali I korunur)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def _kat(baslik, ks):
    for k in ks:
        if _buyut(k) == (baslik.get("adMetni") or ""):
            return k
    return None


def _sayisiz_ve_ayni(r, taban):
    """Sayi HIC basilmamis + JS hatasi yok + panel/ad kumesi tabanla BIREBIR ayni mi?"""
    if r.get("_cokme") or r.get("hata") is not None or r.get("konsolHatalari"):
        return False
    b = r.get("basliklar") or []
    t = taban.get("basliklar") or []
    if not b or len(b) != len(t):
        return False
    if any(x.get("sayiOgeAdedi") for x in b):
        return False
    if any((x.get("metin") or "") != (x.get("adMetni") or "") for x in b):
        return False
    return ([(x.get("adMetni"), x.get("sinif"), x.get("href")) for x in b]
            == [(x.get("adMetni"), x.get("sinif"), x.get("href")) for x in t])


def _fark_ozeti(r, taban):
    b = r.get("basliklar") or []
    return ("cokme=%r hata=%r konsol=%s panel=%d/%d sayili=%d ornek=%r"
            % (r.get("_cokme"), r.get("hata"), r.get("konsolHatalari"),
               len(b), len(taban.get("basliklar") or []),
               sum(1 for x in b if x.get("sayiOgeAdedi")),
               (b[0].get("metin") if b else None)))


# ---------------------------------------------------------------- mutasyon
# (dosya, eski, yeni, beklenen, aciklama)
MUTANTLAR = [
    # --- FAIL-CLOSED kolu (istemci) ---
    ("index.html",
     '    if(!ix || !ix.katSayisi){ return null; }',
     '    if(!ix){ return null; }', "KIRMIZI",
     "FAIL-OPEN: alan yokken okuyucu COKER -> eski gomulu indeksle yayinlanan sayfada "
     "TUM kategori panelleri kaybolur (D14)"),
    ("index.html",
     '    return (typeof n === "number" && isFinite(n) && n > 0 && n === Math.floor(n)) ? n : null;',
     '    return n ? n : null;', "KIRMIZI",
     "FAIL-OPEN: tip/isaret/ondalik kapisi kalkar -> musteriye '1901 ürün' yerine "
     "dizge/ondalik/negatif basilir (D15)"),
    # --- HARDCODE sinifi (istegin ASIL sarti) ---
    ("index.html",
     '        sayiEl.textContent = " " + katN + " ürün";',
     '        sayiEl.textContent = " 1901 ürün";', "KIRMIZI",
     "HARDCODE: bugun Marin'de DOGRU gorunur, her kategoride ve her yeni urunde YALAN "
     "olur (D10 + D16)"),
    ("cip-indeks.py",
     "            kat_sayisi[kat] = kat_sayisi.get(kat, 0) + n",
     "            kat_sayisi[kat] = kat_sayisi.get(kat, 0) + 1", "KIRMIZI",
     "SAYIM BIRIMI KAYAR: kategori toplami yerine ALT KIRILIM ADEDI sayilir (D2/D3/D9)"),
    # 🔴 BU MUTANT COKMEZ, SESSIZCE YANLIS SAYAR — oncul notunun uyardigi mukerrer-sayim
    # yolunun ta kendisi. `kat_marka` da (kat, X) -> n bicimindedir, yani ayni dongude
    # SORUNSUZ acilir; cok markali urun BIRDEN FAZLA, markasiz urun HIC sayilir. Bu
    # yuzden fikstur bilerek 2 markali ve markasiz kayit tasir (yoksa mutant fiksturde
    # ESDEGER olur ve eksen olculmemis kalirdi).
    ("cip-indeks.py",
     "    for (kat, _altk), n in kat_alt.items():",
     "    for (kat, _altk), n in kat_marka.items():", "KIRMIZI",
     "MUKERRER SAYIM: sayim URUN bazli tablodan MARKA bazli tabloya kayar -> cok markali "
     "urun iki kez, markasiz urun HIC sayilir (D2/D3/D5/D9)"),
    ("cip-indeks.py",
     '            "katSayisi": kat_sayisi}',
     '            "katSayisiX": kat_sayisi}', "KIRMIZI",
     "ALAN ADI KAYAR: uretec bir sey uretir, istemci HICBIR sey gormez -> sessiz "
     "'ozellik yok' hali (D1/D6/D10)"),
    ("tools-kosum",
     '      .filter((c) => String(c.className) === "kat-panel-sayi");',
     '      .filter((c) => String(c.className).indexOf("kat-panel-sayi") !== -1);',
     "YESIL",
     "KONTROL: kosumun sinif suzgeci GEVSER ama canli sinif dogru oldugu icin sonuc "
     "degismez — iddialar suzgec BICIMINE pinlenmemeli"),
    ("index.html",
     '    sayiEl.className = "kat-panel-sayi";',
     '    sayiEl.className = "kat-panel-sayi-x";', "KIRMIZI",
     "CSS KANCASI KOPAR: sayi basilir ama 46px baslik puntosu/harf araligiyla cizilir, "
     "mobilde basligi kirar (D11)"),
    # --- KONTROL MUTANTLARI (YESIL bekleniyor) — iddialar ILGISIZ degisikliklere
    # PINLENMIS mi? Yesil kalmazlarsa kapi asiri-baglanmistir.
    ("index.html",
     '    color:var(--gray-text);\n    white-space:nowrap;',
     '    color:var(--navy-2);\n    white-space:nowrap;', "YESIL",
     "ILGISIZ: sayinin rengi — davranisa/sayiya DOKUNMAZ"),
    ("cip-indeks.py",
     "    kat_sayisi = {}\n    for (kat, _altk), n in kat_alt.items():",
     "    kat_sayisi = dict()\n    for (kat, _altk), n in kat_alt.items():", "YESIL",
     "KONTROL: esdeger sozluk kurulusu — davranis birebir ayni"),
]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _hedef(tmp, dosya):
    if dosya == "index.html":
        return os.path.join(tmp, "index.html")
    if dosya == "tools-kosum":
        return os.path.join(tmp, "tools", "kat-sayisi-kosum.js")
    return os.path.join(tmp, "tools", dosya)


def _kopya_kur():
    """index.html + tools/ KOPYALANIR (mutant oraya yazilir), kalani SYMLINK."""
    tmp = tempfile.mkdtemp(prefix="pruvo-kat-sayisi-mut-")
    shutil.copytree(os.path.join(GERCEK_KOK, "tools"), os.path.join(tmp, "tools"))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git", ".claude"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    izlenen = [os.path.join(GERCEK_KOK, "index.html"),
               os.path.join(GERCEK_KOK, "tools", "cip-indeks.py"),
               os.path.join(GERCEK_KOK, "tools", "kat-sayisi-kosum.js"),
               os.path.join(GERCEK_KOK, "urunler.json")]
    once = {y: _sha(y) for y in izlenen}
    basarisiz = []

    # M00 MUTASYONSUZ KONTROL — harness saglam mi (yoksa tum KIRMIZI'lar YALANCI).
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s"
          % ("OK  " if p0.returncode == 0 else "HATA",
             "YESIL" if p0.returncode == 0 else "KIRMIZI"))
    if p0.returncode != 0:
        for s in (p0.stdout or "").splitlines():
            if s.strip().startswith("KALDI"):
                print("     " + s.strip()[:220])
        print("     " + ((p0.stderr or "").strip().splitlines() or [""])[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = _kopya_kur()
        hedef = _hedef(tmp, dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        sayi = metin.count(eski)
        # 🔴 CAPA KAYMASI = KIRMIZI, "gecti" DEGIL: eslesmeyen capa o ekseni OLCMEMISTIR.
        if sayi != 1:
            basarisiz.append("M%02d CAPA BAYAT (%d eslesme) %s" % (i, sayi, dosya))
            print("  HATA M%02d [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("M%02d %s: KIRMIZI ama HICBIR iddia KALDI demedi (cokme)" % (i, dosya))
        print("  %s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
              % ("OK  " if goruldu == beklenen else "HATA", i, beklenen, dosya, goruldu,
                 len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:190])
        shutil.rmtree(tmp, ignore_errors=True)

    sonra = {y: _sha(y) for y in izlenen}
    bozuk = [os.path.basename(y) for y in once if once[y] != sonra[y]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    print("  MUTANT FIILEN UYGULANDI: %d/%d" % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK, help="agac (mutasyon kopyasi icin)")
    ap.add_argument("--mutasyon", action="store_true", help="cift yonlu mutasyon (elle)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== KATEGORI PANEL BASLIGI URUN SAYISI KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())
