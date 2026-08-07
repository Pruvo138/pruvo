#!/usr/bin/env python3
"""r2-onek-mutasyon.py — r2-onek-gelenek-kapisi.py icin MUTASYON CURUTME SURUCUSU.

NEDEN: "testler yesil" tek basina kanit degil ([[test-hatali-davranisi-kutsar]]). Bu surucu
tools/r2_anahtar.py + tools/gorsel-cakisma-onar.py + tools/r2-onek-gelenek-kapisi.py'ye
BILEREK hata enjekte eder ve kapinin o hatayi YAKALAYIP YAKALAMADIGINI olcer.

🔴 BAGIMSIZ CURUTME (7 Agu 2026) ILK BATARYAYI KIRDI — 8 dusmanca mutanttan 5'i SAG KALMISTI
(hash no-op · hash no-op + gizli muafiyet · iddia atlama + sayac sabitleme · tarama yuzeyi
daraltma · regex korlestirme) ve 7 iddiadan 4'u hicbir mutantla BAGIMSIZ olarak olmuyordu.
Bu surum uc kusuru onarir:

  (1) 🔴 KABUL CIKIS KODU DEGIL, BASILAN SAYI+KIMLIK. Kapi bugun ZATEN KIRMIZI (canlida
      olculen B2 + E3 gercekleri). Cikis kodunu karsilastiran bir batarya bu yuzden HICBIR
      SEY olcemez. Burada kabul = kapinin bastigi KIRMIZI IDDIA KIMLIKLERI kumesinin
      TABANDAN FARKI ([[kapi-yan-etkisi-gizli-onkosul]]: cikis kodunu degil BASTIGI SAYIYI
      karsilastir).
  (2) 🔴 HER KOSUMDA SAYIM DOGRULANIR: kapinin bastigi "IDDIA: N" ile stdout'ta FIILEN
      basilan iddia satiri sayisi ve IDDIA_TABANI karsilastirilir. "Iddia atla + sayaci
      sabitle" mutanti tam burada olur ([[mutasyon-kaniti-yeniden-uretilebilir]]).
      TARANAN_KAYIT de ayni sekilde disaridan karsilastirilir (yuzey daraltma mutanti).
  (3) 🔴 AYIRT EDICILIK OLCULUR: her oldurucu mutantin TABANDAN FARKI (delta) tek tek
      basilir. Bir iddia ancak DELTASI TAM OLARAK KENDISI olan bir mutant varsa "bagimsiz
      kanitlanmis" sayilir ([[beyan-edilmis-survivor]]: ayirt edici mutant yoksa eksen ayri
      bir iddia degildir). Kapanista AYRISMAYAN_IDDIA sayisi basilir; 0 degilse KIRMIZI.

⚠️ BYTECODE ONBELLEK TUZAGI ([[mutasyon-bytecode-onbellegi]]): ayni uzunlukta bir mutasyon
ayni saniyede AYNI YOLA yazilirsa .pyc onbellegi eski derlemeyi geri verebilir. Uc katman:
  1. her mutant kendi mkdtemp() dizinine yazilir (yol asla tekrarlanmaz),
  2. alt surec `-B` + PYTHONDONTWRITEBYTECODE=1 ile kosar,
  3. S1 sentinel: ayni uzunlukta iki farkli mutasyon + mutasyonsuz kosum ARKA ARKAYA.

Kosum:  python3 tools/r2-onek-mutasyon.py
Cikis kodu: 0 = butun oldurucu mutantlar BEKLENEN DELTA ile oldu + butun kontrol mutantlari
tabanla BIREBIR AYNI + sayim/ayirt-edicilik sartlari saglandi; 1 = aksi.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
URUNLER = os.path.join(ROOT, "urunler.json")

R2_SRC = open(os.path.join(HERE, "r2_anahtar.py"), encoding="utf-8").read()
GATE_SRC = open(os.path.join(HERE, "r2-onek-gelenek-kapisi.py"), encoding="utf-8").read()
ONAR_SRC = open(os.path.join(HERE, "gorsel-cakisma-onar.py"), encoding="utf-8").read()

#: E1 (ikiz-tanim) icin BILEREK enjekte edilen sahte kopya — fikstur SAGLIK kaniti icin.
IKIZ_FIKSTUR = (
    "# fikstur: ikiz-tanim tespiti icin BILEREK enjekte edilmis kopya (r2-onek-mutasyon.py yazdi)\n"
    "def _kopya_anahtar(slug):\n"
    "    return \"c3d\" + slug\n"
)

#: E3 POZITIF KONTROLU: onekleri ONEKLER ile UYUSAN sentetik ikiz kaynagi. E3'un "takili
#: kirmizi" (tautoloji) olmadigini, uyum halinde YESIL yandigini kanitlar.
UYUMLU_IKIZ_KAYNAK = '''PLATFORMLAR = {
    "makerworld": {"ad": "MakerWorld", "onek": "mw"},
    "printables": {"ad": "Printables", "onek": "pr"},
    "thingiverse": {"ad": "Thingiverse", "onek": "th"},
    "cgtrader": {"ad": "CGTrader", "onek": "cgt-", "api_yok": True},
    "cults3d": {"ad": "Cults3D", "onek": "c3d"},
}
'''

IDDIA_SATIR_RE = re.compile(r"^  (OK|KIRMIZI)\s+([A-Z]\d)\. ")

sonuclar = []          # (ad, tur, ok)
oldurucu_deltalar = {}  # ad -> frozenset(delta)


# ══════════════════════════════════════════════════════════════════════ kosum altyapisi
def _yaz(dizin, ad, metin):
    with open(os.path.join(dizin, "tools", ad), "w", encoding="utf-8") as f:
        f.write(metin)


def _hazirla(r2=None, gate=None, onar=None, fikstur=False, ikiz=None):
    d = tempfile.mkdtemp(prefix="r2onek-mutant-")
    os.makedirs(os.path.join(d, "tools"))
    _yaz(d, "r2_anahtar.py", r2 if r2 is not None else R2_SRC)
    _yaz(d, "r2-onek-gelenek-kapisi.py", gate if gate is not None else GATE_SRC)
    _yaz(d, "gorsel-cakisma-onar.py", onar if onar is not None else ONAR_SRC)
    if fikstur:
        _yaz(d, "sahte-ikiz-anahtar.py", IKIZ_FIKSTUR)
    ikiz_yolu = None
    if ikiz is not None:
        ikiz_yolu = os.path.join(d, "sentetik_hasat_ortak.py")
        with open(ikiz_yolu, "w", encoding="utf-8") as f:
            f.write(ikiz)
    return d, ikiz_yolu


def kos(**kw):
    """Kapiyi mutant kopyayla kosturur; MAKINE-OKUNUR olcumu geri dondurur."""
    dizin, ikiz_yolu = _hazirla(**kw)
    try:
        env = dict(os.environ)
        env["PRUVO_ROOT"] = dizin
        env["PRUVO_URUNLER_JSON"] = URUNLER
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if ikiz_yolu:
            env["PRUVO_HASAT_ORTAK"] = ikiz_yolu
        p = subprocess.run(
            [sys.executable, "-B", os.path.join(dizin, "tools", "r2-onek-gelenek-kapisi.py")],
            env=env, capture_output=True, text=True, timeout=180)
    finally:
        shutil.rmtree(dizin, ignore_errors=True)

    out = p.stdout
    # 🔴 BAGIMSIZ SAYIM: kapinin bastigi sayiya DEGIL, fiilen basilan satirlara bakilir.
    satirlar = [m.group(2) for m in
                (IDDIA_SATIR_RE.match(s) for s in out.splitlines()) if m]
    kirmizi_satir = set(m.group(2) for m in
                        (IDDIA_SATIR_RE.match(s) for s in out.splitlines()) if m and m.group(1) == "KIRMIZI")

    def _sayi(anahtar, kalip):
        m = re.search(kalip, out, re.M)
        return int(m.group(1)) if m else -1

    basilan = _sayi("iddia", r"^IDDIA: (\d+)")
    taban = _sayi("taban", r"^IDDIA: \d+ \(taban (\d+)\)")
    kayit = _sayi("kayit", r"TARANAN_KAYIT=(\d+)")
    m = re.search(r"^KIRMIZI_IDDIALAR: (.+)$", out, re.M)
    basilan_kirmizi = set() if (not m or m.group(1).strip() == "-") else set(
        x.strip() for x in m.group(1).split(","))
    return {"rc": p.returncode, "satir_iddia": len(satirlar), "basilan_iddia": basilan,
            "taban": taban, "kayit": kayit, "kirmizi": kirmizi_satir,
            "basilan_kirmizi": basilan_kirmizi, "out": out, "err": p.stderr}


def _sayim_ihlali(o):
    """Kapinin KENDI raporlamasinin tutarliligi — her kosumda, mutantta da tabanda da."""
    ihlal = []
    if o["satir_iddia"] != o["basilan_iddia"]:
        ihlal.append("basilan IDDIA=%d ama fiilen %d iddia satiri var (SAYAC SABITLENMIS?)"
                     % (o["basilan_iddia"], o["satir_iddia"]))
    if o["basilan_iddia"] < o["taban"]:
        ihlal.append("IDDIA %d < taban %d" % (o["basilan_iddia"], o["taban"]))
    if o["kirmizi"] != o["basilan_kirmizi"]:
        ihlal.append("KIRMIZI_IDDIALAR ozeti (%s) satirlarla (%s) uyusmuyor"
                     % (sorted(o["basilan_kirmizi"]), sorted(o["kirmizi"])))
    return ihlal


def _delta(taban, olcum):
    return frozenset(["+" + k for k in (olcum["kirmizi"] - taban["kirmizi"])]
                     + ["-" + k for k in (taban["kirmizi"] - olcum["kirmizi"])])


def _bas(ad, tur, ok, not_=""):
    print("%-8s %-8s %s%s" % ("OK" if ok else "KIRMIZI", "[" + tur + "]", ad,
                              ("  -> " + not_) if not_ else ""))
    sonuclar.append((ad, tur, ok))
    return ok


# ══════════════════════════════════════════════════════════════════════ TABAN (mutasyonsuz)
print("=" * 100)
print("TABAN OLCUMU (mutasyonsuz kapi, GERCEK katalog + GERCEK ikiz kaynagi)")
print("=" * 100)
TABAN = kos()
_ihlal = _sayim_ihlali(TABAN)
_bas("T0 TABAN: kapi kendi sayimini tutarli basiyor (iddia satiri == IDDIA == >=taban)",
     "taban", not _ihlal, "; ".join(_ihlal))
print("     TABAN kirmizi iddialar: %s · iddia=%d (taban %d) · TARANAN_KAYIT=%d · rc=%d"
      % (",".join(sorted(TABAN["kirmizi"])) or "-", TABAN["basilan_iddia"], TABAN["taban"],
         TABAN["kayit"], TABAN["rc"]))
print("     (B2 = canlida 1 'x' onekli kayit · E3 = CGTrader ikiz ayrismasi — ikisi de")
print("      OLCULEN GERCEK, kapinin hatasi DEGIL. Mutant kabulu bu tabanla KARSILASTIRILIR.)")
TABAN_FIKSTURLU = kos(fikstur=True)

# TABAN saglik: fikstur eklenince E1 KIRMIZI olmali (E1 gercekten calisiyor, tautoloji degil)
_bas("T1 TABAN-SAGLIK: sahte ikiz fikstürü eklenince E1 KIRMIZI (E1 fiilen tariyor)", "taban",
     _delta(TABAN, TABAN_FIKSTURLU) == frozenset(["+E1"]),
     "delta=%s" % sorted(_delta(TABAN, TABAN_FIKSTURLU)))

# TABAN saglik: uyumlu sentetik ikizle E3 YESILE doner (E3 "takili kirmizi" degil)
_uyumlu = kos(ikiz=UYUMLU_IKIZ_KAYNAK)
_bas("T2 TABAN-SAGLIK: onekleri UYUSAN sentetik ikizle E3 YESIL (E3 takili-kirmizi degil)",
     "taban", _delta(TABAN, _uyumlu) == frozenset(["-E3"]),
     "delta=%s" % sorted(_delta(TABAN, _uyumlu)))


# ══════════════════════════════════════════════════════════════════════ mutant kosucusu
def oldurucu(ad, beklenen_delta, taban=None, **kw):
    t = taban or TABAN
    o = kos(**kw)
    d = _delta(t, o)
    beklenen = frozenset(beklenen_delta)
    ihlal = _sayim_ihlali(o)
    ok = (d == beklenen) and not ihlal
    oldurucu_deltalar[ad] = d
    return _bas(ad, "oldurucu", ok,
                "delta=%s (beklenen %s)%s" % (sorted(d), sorted(beklenen),
                                              (" · SAYIM: " + "; ".join(ihlal)) if ihlal else ""))


def kontrol(ad, **kw):
    """Davranisi DEGISTIRMEYEN mutant: taban ile BIREBIR ayni olmali (delta bos + sayimlar ayni)."""
    o = kos(**kw)
    d = _delta(TABAN, o)
    ok = (not d and o["basilan_iddia"] == TABAN["basilan_iddia"]
          and o["kayit"] == TABAN["kayit"] and not _sayim_ihlali(o))
    return _bas(ad, "kontrol", ok, "delta=%s iddia=%d kayit=%d"
                % (sorted(d), o["basilan_iddia"], o["kayit"]))


def _yama(kaynak, hedef, yeni, etiket):
    assert hedef in kaynak, "MUTASYON UYGULANAMADI (%s) — kaynak degisti mi?" % etiket
    return kaynak.replace(hedef, yeni, 1)


# ══════════════════════════════════════════════════════════════════════ OLDURUCU MUTANTLAR
print("")
print("=" * 100)
print("OLDURUCU MUTANTLAR — her biri TABANDAN FARKI (delta) ile kabul edilir")
print("=" * 100)

# ── A1
oldurucu("M01 A1: ONEKLER'den Cults3D SILINDI", ["+A1"],
         r2=_yama(R2_SRC, '    "Cults3D": "c3d",\n', "", "M01"))
oldurucu("M02 A1: Cults3D oneki YANLIS yazildi (c3d -> c3x)", ["+A1"],
         r2=_yama(R2_SRC, '"Cults3D": "c3d",', '"Cults3D": "c3x",', "M02"))

# ── B1
oldurucu("M03 B1: gelenek kapisinin kolu TERSINE cevrildi", ["+B1"],
         gate=_yama(GATE_SRC,
                    'sonuc("B1", "muafiyet disinda sayisal-govdeli c3d anahtari yok", not yeni,',
                    'sonuc("B1", "muafiyet disinda sayisal-govdeli c3d anahtari yok", bool(yeni),',
                    "M03"))

# ── B2  (ASIL VEKTOR — tabanda KIRMIZI; no-op yapilinca kirmizi KAYBOLUR = kill)
oldurucu("M04 B2: 'x' onek ekseni no-op yapildi (asil vektor korlestirildi)", ["-B2"],
         gate=_yama(GATE_SRC, "          not x_ihlal,", "          True,  # MUTANT no-op",
                    "M04"))

# ── B3  (yuzey daraltma, BULGULAR korunarak -> yalniz yuzey sayaci duser)
oldurucu("M05 B3: tarama yuzeyi sessizce daraltildi (bulgular korunur, sayac duser)", ["+B3"],
         gate=_yama(GATE_SRC,
                    '        _olcum["kayit"] += 1\n',
                    '        if not any(("/urunler/c3d" in g) or ("/urunler/x" in g)\n'
                    '                   for g in (u.get("gorseller") or [])):\n'
                    '            continue  # MUTANT: yuzey daraltmasi\n'
                    '        _olcum["kayit"] += 1\n',
                    "M05"))

# ── B4  (siniflandirici, canli veriyi ETKILEMEYEN ince korlestirme)
oldurucu("M06 B4: sayisal-govde regex'i ince korlestirildi (\\d+ -> \\d*)", ["+B4"],
         gate=_yama(GATE_SRC, r'return bool(re.match(r"^%s\d+$"',
                    r'return bool(re.match(r"^%s\d*$"', "M06"))

# ── C1
oldurucu("M07 C1: FROZEN_MUAFIYET BEKLENEN HASH sabiti bozuldu", ["+C1"],
         gate=_yama(GATE_SRC,
                    '"ebcbd155bdaaa9e7c51370ccf0e4d2cd8bb62214bccf06b3465217324c96bd81"',
                    '"' + "0" * 64 + '"', "M07"))

# ── C2  (curutucunun SAG KALAN mutanti: hash HEDEFLI no-op + len guncellemesi + gizli muafiyet)
_m08 = _yama(GATE_SRC,
             '    kanon = "\\n".join(sorted(anahtarlar))\n'
             '    return hashlib.sha256(kanon.encode("utf-8")).hexdigest()',
             '    if anahtarlar is FROZEN_MUAFIYET:  # MUTANT: HEDEFLI no-op (C3 fiksturu etkilenmez)\n'
             '        return FROZEN_MUAFIYET_BEKLENEN_HASH\n'
             '    kanon = "\\n".join(sorted(anahtarlar))\n'
             '    return hashlib.sha256(kanon.encode("utf-8")).hexdigest()', "M08a")
_m08 = _yama(_m08, "FROZEN_MUAFIYET_BEKLENEN_UZUNLUK = 15",
             "FROZEN_MUAFIYET_BEKLENEN_UZUNLUK = 16", "M08b")
_m08 = _yama(_m08, '    "c3d933757",\n]',
             '    "c3d933757",\n    "c3d9999999",  # MUTANT: GIZLI muafiyet\n]', "M08c")
oldurucu("M09 C2: hash HEDEFLI no-op + len guncellendi + GIZLI muafiyet eklendi", ["+C2"],
         gate=_m08)

# ── C3  (curutucunun SAG KALAN mutanti: hash fonksiyonu tamamen no-op)
oldurucu("M10 C3: hash fonksiyonu no-op (daima beklenen sabiti dondurur)", ["+C3"],
         gate=_yama(GATE_SRC,
                    '    kanon = "\\n".join(sorted(anahtarlar))\n'
                    '    return hashlib.sha256(kanon.encode("utf-8")).hexdigest()',
                    '    return FROZEN_MUAFIYET_BEKLENEN_HASH  # MUTANT: no-op', "M10"))

# ── D1 / D2
oldurucu("M11 D1: fail-closed yolu sessize cevrildi", ["+D1"],
         r2=_yama(R2_SRC,
                  "    if platform not in ONEKLER:\n        if not bilinmeyen_sessiz:\n",
                  "    if platform not in ONEKLER:\n        if not bilinmeyen_sessiz and False:  # MUTANT\n",
                  "M11"))
oldurucu("M12 D2: BILINMEYEN_ONEK degeri kaydi ('x' -> 'z')", ["+D2"],
         r2=_yama(R2_SRC, 'BILINMEYEN_ONEK = "x"', 'BILINMEYEN_ONEK = "z"  # MUTANT', "M12"))

# ── E1  (fikstürlü tabana gore: kirmizi KAYBOLUR = kill)
oldurucu("M13 E1: ikiz-tanim taramasi no-op yapildi (fikstürlü tabana gore)", ["-E1"],
         taban=TABAN_FIKSTURLU, fikstur=True,
         gate=_yama(GATE_SRC,
                    '    sonuc("E1", "aktif tools/ kodunda satir-ici Cults3D anahtar-turetme kopyasi yok",\n'
                    '          not bulunanlar, "; ".join(bulunanlar[:8]))',
                    '    sonuc("E1", "aktif tools/ kodunda satir-ici Cults3D anahtar-turetme kopyasi yok",\n'
                    '          True, "MUTANT: bulgu goz ardi edildi")', "M13"))

# ── E2
oldurucu("M14 E2: gorsel-cakisma-onar.py'den bilinmeyen_sessiz=True kaldirildi", ["+E2"],
         onar=_yama(ONAR_SRC,
                    "    return r2k.gkey(platform, sid, yedek=False, bilinmeyen_sessiz=True)",
                    "    return r2k.gkey(platform, sid, yedek=False)  # MUTANT", "M14"))

# ── E3  (tabanda KIRMIZI; no-op yapilinca kaybolur = kill)
oldurucu("M15 E3: GERCEK ikiz ayrisma kontrolu no-op yapildi", ["-E3"],
         gate=_yama(GATE_SRC,
                    '        sonuc("E3", "gercek ikiz (hasat_ortak.PLATFORMLAR) ile ONEKLER ayrismamis",\n'
                    '              not ayrismalar,',
                    '        sonuc("E3", "gercek ikiz (hasat_ortak.PLATFORMLAR) ile ONEKLER ayrismamis",\n'
                    '              True,  # MUTANT no-op', "M15"))

# ── E4  (ikiz ayrıştırıcısı korlestirilirse E3 FAIL-CLOSED kirmizi KALIR, E4 yanar)
oldurucu("M16 E4: gercek ikiz ayrıştırıcısı korlestirildi (0 platform)", ["+E4"],
         gate=_yama(GATE_SRC,
                    "PLATFORM_SATIR_RE = re.compile(\n",
                    "PLATFORM_SATIR_RE = re.compile(r'ZZ_HICBIR_SEY_ZZ')  # MUTANT\n"
                    "_KULLANILMAYAN = re.compile(\n", "M16"))

# ── CURUTUCUNUN AGRESIF SAG KALANLARI (delta genis, ama YAKALANMALI)
oldurucu("M17 [curutucu] tarama yuzeyi TEK urune daraltildi", ["+B3", "+C2", "-B2"],
         gate=_yama(GATE_SRC, "    for u in urunler:", "    for u in urunler[:1]:  # MUTANT",
                    "M17"))
oldurucu("M18 [curutucu] siniflandirici tamamen korlestirildi (daima False)", ["+B4", "+C2"],
         gate=_yama(GATE_SRC, r'    return bool(re.match(r"^%s\d+$" % re.escape(o), anahtar))',
                    "    return False  # MUTANT", "M18"))

# M19: iddia ATLA + sayaci SABITLE -> delta BOS, cikis kodu AYNI; YALNIZ bagimsiz SAYIM yakalar
_m19 = _yama(GATE_SRC, "test_d(_ciftler)", "pass  # MUTANT: 2 iddia atlandi", "M19a")
_m19 = _yama(_m19, "_toplam = len(_iddialar)",
             "_toplam = IDDIA_TABANI  # MUTANT: sayac sabitlendi", "M19b")
_o19 = kos(gate=_m19)
_i19 = _sayim_ihlali(_o19)
oldurucu_deltalar["M19"] = _delta(TABAN, _o19)
_bas("M19 [curutucu] SAYIM: 2 iddia atlandi + sayac sabitlendi (delta BOS — yalniz sayim yakalar)",
     "oldurucu", bool(_i19) and _o19["satir_iddia"] < TABAN["satir_iddia"],
     "delta=%s · sayim ihlali=%s · satir iddia %d -> %d"
     % (sorted(_delta(TABAN, _o19)), "; ".join(_i19) or "YOK",
        TABAN["satir_iddia"], _o19["satir_iddia"]))

# ══════════════════════════════════════════════════════════════════════ KONTROL MUTANTLAR
print("")
print("=" * 100)
print("KONTROL MUTANTLAR — davranisi DEGISTIRMEZ, tabanla BIREBIR ayni kalmali")
print("=" * 100)
kontrol("K1 KONTROL: r2_anahtar.py'de sadece yorum degisti",
        r2=_yama(R2_SRC, "#: platform adi -> R2 anahtar oneki.",
                 "#: platform adi -> R2 anahtar oneki (KONTROL: yalniz yorum).", "K1"))
kontrol("K2 KONTROL: ONEKLER'e alakasiz platform eklendi (GrabCAD)",
        r2=_yama(R2_SRC, '    "Cults3D": "c3d",\n}',
                 '    "Cults3D": "c3d",\n    "GrabCAD": "gc",  # KONTROL\n}', "K2"))
kontrol("K3 KONTROL: kapiya davranissiz yorum satiri eklendi",
        gate=_yama(GATE_SRC, "hatalar = []", "# KONTROL: davranissiz yorum\nhatalar = []", "K3"))
kontrol("K4 KONTROL: gorsel-cakisma-onar.py docstring'i degisti",
        onar=_yama(ONAR_SRC, '"""Anahtar turetme TEK KAYNAK', '"""KONTROL. Anahtar turetme TEK KAYNAK',
                   "K4"))

# ══════════════════════════════════════════════════════════════════════ S1 BYTECODE KANITI
print("")
print("=" * 100)
print("S1 BYTECODE ONBELLEK KANITI — ayni uzunlukta 3 ardisik kosum")
print("=" * 100)
_s1a = kos(r2=_yama(R2_SRC, '"Cults3D": "c3d",', '"Cults3D": "c3x",', "S1a"))
_s1b = kos(r2=_yama(R2_SRC, '"Cults3D": "c3d",', '"Cults3D": "c3y",', "S1b"))
_s1c = kos()
_s1_ok = (_delta(TABAN, _s1a) == frozenset(["+A1"])
          and _delta(TABAN, _s1b) == frozenset(["+A1"])
          and _delta(TABAN, _s1c) == frozenset())
_bas("S1 bytecode onbellek tuzagi ele alindi (c3x, c3y, mutasyonsuz ardisik ve tutarli)",
     "kanit", _s1_ok,
     "deltalar: %s / %s / %s" % (sorted(_delta(TABAN, _s1a)), sorted(_delta(TABAN, _s1b)),
                                 sorted(_delta(TABAN, _s1c))))

# ══════════════════════════════════════════════════════════════════════ AYIRT EDICILIK
print("")
print("=" * 100)
print("AYIRT EDICILIK — her iddianin DELTASI TAM OLARAK KENDISI olan bir mutanti var mi?")
print("=" * 100)
TUM_IDDIALAR = ["A1", "B1", "B2", "B3", "B4", "C1", "C2", "C3", "D1", "D2", "E1", "E2", "E3", "E4"]
ayrismayan = []
for _iddia in TUM_IDDIALAR:
    _sahipler = [ad for ad, d in oldurucu_deltalar.items()
                 if d in (frozenset(["+" + _iddia]), frozenset(["-" + _iddia]))]
    if _sahipler:
        print("  AYRISTI   %-3s <- %s" % (_iddia, ", ".join(sorted(_sahipler))))
    else:
        ayrismayan.append(_iddia)
        print("  AYRISMADI %-3s <- (tek basina dusuren mutant YOK)" % _iddia)
_bas("AYIRT EDICILIK: her iddia tek basina dusurulebiliyor", "ayirt", not ayrismayan,
     "ayrismayan=%s" % (ayrismayan or "YOK"))

# ══════════════════════════════════════════════════════════════════════════════ KAPANIS
print("")
_old = [(a, o) for a, t, o in sonuclar if t == "oldurucu"]
_kon = [(a, o) for a, t, o in sonuclar if t == "kontrol"]
_dig = [(a, o) for a, t, o in sonuclar if t not in ("oldurucu", "kontrol")]
_basarisiz = [a for a, t, o in sonuclar if not o]
print("OLDURUCU: %d/%d · KONTROL: %d/%d · TABAN+KANIT+AYIRT: %d/%d · AYRISMAYAN_IDDIA: %d"
      % (sum(1 for _, o in _old if o), len(_old), sum(1 for _, o in _kon if o), len(_kon),
         sum(1 for _, o in _dig if o), len(_dig), len(ayrismayan)))
print("TABAN_KIRMIZI: %s (canlida OLCULEN gercek — kapinin kusuru degil)"
      % (",".join(sorted(TABAN["kirmizi"])) or "-"))
if _basarisiz:
    print("KIRMIZI — %d beklenmedik: %s" % (len(_basarisiz), "; ".join(_basarisiz)))
    sys.exit(1)
print("YESIL — butun oldurucular beklenen delta ile oldu, kontroller tabanla birebir,"
      " ayrismayan iddia yok")
sys.exit(0)
