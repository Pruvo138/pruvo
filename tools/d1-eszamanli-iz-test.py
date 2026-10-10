#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — K434 D1 senkron ESZAMANLILIK IZI (`tools/d1-sync.py::eszamanli_izli`).

  python3 tools/d1-eszamanli-iz-test.py

NEDEN: K434 (5 Eki) eszamanli >=3 parti push'unda pre-push D1 senkronu SEQ TUKENDI /
YEREL_YARIS ile kilitlendi; sinif onarimi main'de ama "canli >=3 eszamanli push" olcutu
IZ OLMADIGI icin olculemedi. Iz: her CLI senkron kosumu ortak git dizinindeki
`d1-eszamanli.log`'a TEK satir ekler; +-60 sn penceresinde >=2 kosum varsa ozet basar.

CANLI D1'e / wrangler'a / aga DOKUNMAZ: gecici git deposu (`sentetik_git`, GIT_* temiz),
VERI KOKU oraya cevrilir; senkron govdesi sahte bir cagrilabilirdir.
  V1 tek kosum -> 1 satir, D1_ESZAMANLI basilmaz (+ YAZDI/BOS siniflamasi)
  V2 ayni dakikada 3 kosum -> ucuncusu D1_ESZAMANLI=3
  V3 61 sn arayla 2 kosum -> basmaz
  V4 8 gun eski satir yazimda duser (+ 256 KB tavani en eski yariyi dusurur)
  V5 iz yazilamaz -> senkron rc / SystemExit AYNEN + stderr TEK uyari
  V6 --eszamanli-rapor sayilari fiksturle birebir
  V7 TUKENDI sonuclu kosum -> satir sonuc=TUKENDI, raporda tukendi=1
  V8 CLI: --eszamanli-rapor / --eszamanli-sil (alt surec, D1'siz) + seq_monoton_olc
  M  IZOLE MUTANTLAR (kum kopyasi): (a) pencere 0 -> V2 KIRMIZI · (b) iz hatasi rc'ye
     sizar -> V5 KIRMIZI. SURVIVOR=0 beklenir.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ARACLAR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ARACLAR)
from git_ortami import sentetik_git  # noqa: E402
import veri_kok  # noqa: E402

GERCEK = os.path.join(ARACLAR, "d1-sync.py")
T0 = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)

MUTANTLAR = [
    ("a-pencere-sifir", "IZ_PENCERE_SN = 60\n", "IZ_PENCERE_SN = 0\n", "V2"),
    ("b-iz-hatasi-rcye-sizar",
     "    except (Exception, SystemExit) as e:                           # noqa: BLE001\n"
     "        neden = ",
     "    except (Exception, SystemExit) as e:                           # noqa: BLE001\n"
     "        rc = 1\n"
     "        neden = ", "V5"),
]


def _modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _kos(m, govde, simdi, yol=None):
    """eszamanli_izli'yi kos; (rc, SystemExit kodu ya da None, stdout, stderr) doner."""
    o, e = io.StringIO(), io.StringIO()
    rc, cikis = None, None
    with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
        try:
            rc = m.eszamanli_izli(govde, yol=yol, simdi=simdi)
        except SystemExit as x:
            cikis = x.code
    return rc, cikis, o.getvalue(), e.getvalue()


def _satirlar(yol):
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8") as f:
        return [s for s in f.read().splitlines() if s.strip()]


def vakalar(m, tmp):
    """Her vaka icin (ad, gecti, detay) listesi."""
    sonuc = []

    def dogrula(ad, kosul, detay=""):
        sonuc.append((ad, bool(kosul), detay))

    yol = m.iz_yolu()
    ortak = os.path.join(tmp, ".git")
    dogrula("V0 iz dosyasi ortak git dizininde (yazici kilidinin yani)",
            os.path.dirname(yol) == os.path.realpath(ortak)
            or os.path.dirname(yol) == ortak, yol)

    def sifirla():
        if os.path.exists(yol):
            os.remove(yol)

    def yazan():
        m._IZ["yazilan"] = 3
        return 0

    # V1
    sifirla()
    rc, cikis, o, e = _kos(m, yazan, T0)
    s = _satirlar(yol)
    dogrula("V1 tek kosum -> 1 satir, D1_ESZAMANLI YOK",
            rc == 0 and cikis is None and len(s) == 1 and "D1_ESZAMANLI" not in o
            and " sonuc=YAZDI " in s[0] and " pid=%d " % os.getpid() in s[0]
            and s[0].endswith("seq_monoton=OLCULEMEDI"), "rc=%r s=%r o=%r" % (rc, s, o))
    rc, _c, o, _e = _kos(m, lambda: 0, T0 + timedelta(hours=1))
    s = _satirlar(yol)
    dogrula("V1b yazmayan rc=0 -> sonuc=BOS", len(s) == 2 and " sonuc=BOS " in s[1], repr(s))

    # V2
    sifirla()
    ciktilar = [_kos(m, lambda: 0, T0 + timedelta(seconds=d))[2] for d in (0, 10, 20)]
    dogrula("V2 ayni dakikada 3 kosum -> ucuncusu D1_ESZAMANLI=3",
            ciktilar[0] == "" and ciktilar[1].startswith("D1_ESZAMANLI=2 ")
            and ciktilar[2].strip() == "D1_ESZAMANLI=3 TUKENDI=0 YEREL_YARIS=0 "
                                       "KILIT_BEKLEME_MAX_SN=0.0 SEQ_MONOTON=1",
            repr(ciktilar))

    # V3
    sifirla()
    ciktilar = [_kos(m, lambda: 0, T0 + timedelta(seconds=d))[2] for d in (0, 61)]
    dogrula("V3 61 sn arayla 2 kosum -> basmaz",
            ciktilar == ["", ""] and len(_satirlar(yol)) == 2, repr(ciktilar))

    # V4
    sifirla()
    eski = T0 - timedelta(days=8)
    with open(yol, "w", encoding="utf-8") as f:
        f.write("%s %s pid=1 sonuc=BOS kilit_bekleme_sn=0.0 seq_monoton=1\n"
                % (m.iz_zaman(eski), m.iz_zaman(eski)))
    _kos(m, lambda: 0, T0)
    s = _satirlar(yol)
    dogrula("V4 8 gun eski satir yazimda duser",
            len(s) == 1 and s[0].startswith(m.iz_zaman(T0)), repr(s))
    sifirla()
    dolgu = "%s %s pid=1 sonuc=BOS kilit_bekleme_sn=0.0 seq_monoton=1 %s\n" % (
        m.iz_zaman(T0), m.iz_zaman(T0), "x=" + "y" * 900)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(dolgu * 300)                                     # ~280 KB > 256 KB
    _kos(m, lambda: 0, T0 + timedelta(seconds=5))
    boy = os.path.getsize(yol)
    s = _satirlar(yol)
    dogrula("V4b > 256 KB -> en eski yari duser (kendi satiri kalir)",
            boy <= m.IZ_TAVAN_BAYT and len(s) == 151 and " x=" not in s[-1], "boy=%d n=%d" % (boy, len(s)))

    # V5 — iz yolu bir DIZIN: os.open(O_RDWR) EISDIR
    engel = os.path.join(tmp, "iz-dizin")
    os.makedirs(engel, exist_ok=True)
    rc3, c3, o3, e3 = _kos(m, lambda: 3, T0, yol=engel)
    rc0, c0, _o0, e0 = _kos(m, lambda: 0, T0, yol=engel)

    def patla():
        sys.exit("!! senkron gercek hata")
    rcx, cx, _ox, ex = _kos(m, patla, T0, yol=engel)
    uyari_tek = all(x.count("D1 ESZAMANLI IZI YAZILAMADI") == 1 and x.count("\n") == 1
                    for x in (e3, e0))
    dogrula("V5 iz yazilamaz -> rc AYNEN + stderr TEK uyari",
            rc3 == 3 and c3 is None and rc0 == 0 and c0 is None and o3 == ""
            and rcx is None and cx == "!! senkron gercek hata"
            and "IZI YAZILAMADI" in ex and uyari_tek,
            "rc3=%r rc0=%r cx=%r e3=%r" % (rc3, rc0, cx, e3))

    # V6 — fikstur: kume A (3), kume B (2), tek (1), 8 gun eski (dusmeli), bozuk satir
    sifirla()
    satirlar = []
    for d, sonuc_, seq in ((0, "YAZDI", "1"), (30, "TUKENDI", "OLCULEMEDI"),
                           (50, "YEREL_YARIS", "OLCULEMEDI"), (3600, "YAZDI", "0"),
                           (3640, "BOS", "1"), (7200, "HATA", "OLCULEMEDI")):
        t = T0 + timedelta(seconds=d)
        satirlar.append("%s %s pid=9 sonuc=%s kilit_bekleme_sn=1.5 seq_monoton=%s\n"
                        % (m.iz_zaman(t), m.iz_zaman(t), sonuc_, seq))
    satirlar.append("%s %s pid=9 sonuc=TUKENDI kilit_bekleme_sn=0.0 seq_monoton=0\n"
                    % (m.iz_zaman(eski), m.iz_zaman(eski)))
    satirlar.append("bozuk satir\n")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("".join(satirlar))
    rapor = m.eszamanli_rapor(simdi=T0 + timedelta(hours=3))
    beklenen = ("D1_ESZAMANLI_RAPOR gun=7 kosum=6 eszamanli_olay=2 en_buyuk_n=3 tukendi=1 "
                "yerel_yaris=1 seq_monoton_ihlal=1")
    dogrula("V6 --eszamanli-rapor fiksturle birebir", rapor == beklenen, rapor)

    # V7
    sifirla()

    def tukendi():
        sys.exit("!! SEQ TAM SAYI ARALIGI TUKENDI: x (alt=1 ust=2 k=1). bosluk")
    rc7, c7, _o7, _e7 = _kos(m, tukendi, T0)
    s = _satirlar(yol)
    rapor7 = m.eszamanli_rapor(simdi=T0 + timedelta(minutes=1))
    _kos(m, lambda: 5, T0 + timedelta(seconds=5))
    s2 = _satirlar(yol)
    dogrula("V7 TUKENDI satiri -> raporda tukendi=1 (SystemExit AYNEN)",
            rc7 is None and isinstance(c7, str) and m.TUKENDI_IMZASI in c7
            and len(s) == 1 and " sonuc=TUKENDI " in s[0] and " tukendi=1 " in rapor7
            and len(s2) == 2 and " sonuc=YEREL_YARIS " in s2[1], "%r %r" % (s2, rapor7))

    # V8 — CLI alt surec (D1'siz) + seq_monoton_olc
    ortam = dict(os.environ)
    ortam[veri_kok.ENV_AD] = tmp
    r = subprocess.run([sys.executable, GERCEK_YOL[0], "--eszamanli-rapor"], env=ortam,
                       capture_output=True, text=True, timeout=120)
    sil1 = subprocess.run([sys.executable, GERCEK_YOL[0], "--eszamanli-sil"], env=ortam,
                          capture_output=True, text=True, timeout=120)
    sil2 = subprocess.run([sys.executable, GERCEK_YOL[0], "--eszamanli-sil"], env=ortam,
                          capture_output=True, text=True, timeout=120)
    dogrula("V8 CLI --eszamanli-rapor / --eszamanli-sil",
            r.returncode == 0 and r.stdout.startswith("D1_ESZAMANLI_RAPOR gun=7 ")
            and sil1.returncode == 0 and "D1_ESZAMANLI_SIL=SILINDI" in sil1.stdout
            and sil2.returncode == 0 and "D1_ESZAMANLI_SIL=YOKTU" in sil2.stdout
            and not os.path.exists(yol),
            "%r %r %r" % (r.stdout + r.stderr[-300:], sil1.stdout, sil2.stdout))
    # V9 — KABLO: CLI senkron yazici kolu izi GERCEKTEN yaziyor mu? Sahte `npx` (aga
    # cikmaz, rc=7) -> wrangler cagrisi fail-closed -> rc != 0, satir sonuc=HATA.
    # --durum (yazici DEGIL) satir EKLEMEZ.
    kutu = os.path.join(tmp, "sahte-bin")
    os.makedirs(kutu, exist_ok=True)
    with open(os.path.join(kutu, "npx"), "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\necho sahte-npx >&2\nexit 7\n")
    os.chmod(os.path.join(kutu, "npx"), 0o755)
    ortam9 = dict(ortam)
    ortam9["PATH"] = kutu + os.pathsep + "/usr/bin:/bin"
    for ad_ in ("PRUVO_D1_YARIS_BEKLE_SN", "PRUVO_D1_PUSH_SHA"):
        ortam9.pop(ad_, None)
    r9 = subprocess.run([sys.executable, GERCEK_YOL[0]], env=ortam9, capture_output=True,
                        text=True, timeout=120)
    s9 = _satirlar(yol)
    r9d = subprocess.run([sys.executable, GERCEK_YOL[0], "--durum", "--hizli"], env=ortam9,
                         capture_output=True, text=True, timeout=120)
    dogrula("V9 CLI senkron kolu iz satiri yazar (sonuc=HATA, rc!=0); --durum yazmaz",
            r9.returncode not in (0, None) and len(s9) == 1 and " sonuc=HATA " in s9[0]
            and "D1_ESZAMANLI" not in r9.stdout and len(_satirlar(yol)) == 1
            and r9d.returncode != 0,
            "rc=%r s=%r err=%r" % (r9.returncode, s9, r9.stderr[-400:]))
    sifirla()
    urunler = [{"id": i} for i in ("a", "b", "c", "d")]
    dogrula("V8b seq_monoton_olc: araya dogru atama 1, ters atama 0",
            m.seq_monoton_olc(urunler, {"a": 40, "c": 20, "d": 10}, {"b": 30}) == "1"
            and m.seq_monoton_olc(urunler, {"a": 40, "c": 20, "d": 10}, {"b": 50}) == "0"
            and m.seq_monoton_olc(urunler, {"a": 40}, {}) == "1")
    return sonuc


GERCEK_YOL = [GERCEK]


def bir_kosum(kaynak_yol, ad):
    """Taze gecici git deposu + VERI KOKU -> modulu yukle -> vakalari kos -> temizle."""
    tmp = tempfile.mkdtemp(prefix="d1-eszamanli-iz-")
    eski_ortam = os.environ.get(veri_kok.ENV_AD)
    try:
        p = sentetik_git(tmp, "init", "-q", capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            return [("FIKSTUR git init", False, p.stderr)]
        os.environ[veri_kok.ENV_AD] = tmp
        GERCEK_YOL[0] = kaynak_yol
        m = _modul_yukle(kaynak_yol, ad)
        return vakalar(m, tmp)
    finally:
        GERCEK_YOL[0] = GERCEK
        if eski_ortam is None:
            os.environ.pop(veri_kok.ENV_AD, None)
        else:
            os.environ[veri_kok.ENV_AD] = eski_ortam
        shutil.rmtree(tmp, ignore_errors=True)


def ana():
    kirmizi = 0
    print("[V] CANLI GOVDE")
    for ad, gecti, detay in bir_kosum(GERCEK, "d1_sync_eszamanli_iz"):
        print("  %s %s%s" % ("✅" if gecti else "❌", ad, "" if gecti else "  — " + detay))
        kirmizi += 0 if gecti else 1

    print("\n[M] IZOLE MUTANTLAR (kum kopyasi; canli govde DEGISMEZ)")
    with open(GERCEK, encoding="utf-8") as f:
        kaynak = f.read()
    survivor = 0
    for i, (ad, eski, yeni, hedef) in enumerate(MUTANTLAR, 1):
        if kaynak.count(eski) != 1:
            print("  ❌ %s — capa %d kez gecti (1 olmali)" % (ad, kaynak.count(eski)))
            survivor += 1
            continue
        # Kardes dizin: d1-sync.py kardes modulleri KENDI dizininden cozer.
        kopya = os.path.join(ARACLAR, "_eszamanli_mutant_%d_gecici.py" % i)
        try:
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            sonuc = bir_kosum(kopya, "d1_sync_eszamanli_mutant_%d" % i)
        finally:
            if os.path.exists(kopya):
                os.remove(kopya)
        olen = [a for a, g, _d in sonuc if a.startswith(hedef + " ") and not g]
        if olen:
            print("  ✅ OLDURULDU %s -> %s KIRMIZI" % (ad, olen[0]))
        else:
            survivor += 1
            print("  ❌ HAYATTA KALDI %s -> %s hala YESIL" % (ad, hedef))
    with open(GERCEK, encoding="utf-8") as f:
        degismedi = f.read() == kaynak
    print("  %s CANLI govde mutasyondan etkilenmedi" % ("✅" if degismedi else "❌"))
    kirmizi += 0 if degismedi else 1
    print("\nSONUC: kirmizi=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 0 if kirmizi == 0 and survivor == 0 else 1


if __name__ == "__main__":
    sys.exit(ana())
