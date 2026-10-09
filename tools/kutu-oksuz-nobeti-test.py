#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kutu-oksuz-nobeti-test.py — tools/kutu-oksuz-nobeti.py'nin KABUL TESTI (K424).

NEDEN CI'DA KOSAR: gercek kutu `~/.claude/...` altinda yasar ve CI onu GOREMEZ; ama
olcum kolunun MANTIGI makineden bagimsizdir. Burada kutu kopyalari SENTETIK kurulur,
her hal tek tek enjekte edilir ve hukum olculur. Gercek kutuya YAZILMAZ; kutu-arsivle'ye
verilen kilit/arsiv yollari da fikstur dizinindedir.

VAKALAR (hepsi gecici dizinde, CLI = gercek kullanim sekli):
   1 temiz kutu                                           -> KUTU_OKSUZ_GOVDE=0, rc=0
   2 DIBE basliksiz govde (26 Eyl vakasi)                 -> =1, rc=1, satir no TAM
   3 iki oksuz govde                                      -> =2, rc=1
   4 ORTADA basligi dusmus blok                           -> =1, rc=1
   5 cit icindeki `---`/`## ` (yanlis-pozitif YOK)        -> =0, rc=0
   6 ardisik ayrac / bos bolut (gurultu YOK)              -> =0, rc=0
   7 AYRACSIZ cok bloklu kutu (KOR)                       -> OLCULEMEDI, rc=2, ASLA 0
   8 dosya yok, dizin VAR                                 -> OLCULEMEDI, rc=2
   9 dizin de yok (CI/kosucu)                             -> MAKINEDE_YOK, rc=0
  10 UTF-8 degil                                          -> OLCULEMEDI, rc=2
  11 yarim frontmatter                                    -> OLCULEMEDI, rc=2
  12 saglam frontmatter                                   -> =0 (frontmatter oksuz sayilmaz)
  13 IKIZ TANIM KILIDI: sayi, `kutu-arsivle.py --kuru`nun `oksuz_govde_kutu=`su ile ESIT;
     ayracsiz halde kutu-arsivle `EKSEN_KOR` basar ve burasi OLCULEMEDI der
  14 `--kutu` bir yol beklemeli                           -> OLCULEMEDI, rc=2
  15 gercek kutu DUMEN (smoke): sozlesme satiri bicimi dogru (yaz-yok)
  16 durum.py BAGLANTISI: bolum 10 main()'de CAGRILIR ve satirlar gelir
  17 main() modulden SURULUR (temiz -> 0/rc0, dibe oksuz -> 1/rc1) ve alt surecle ESIT

Kullanim:
    python3 tools/kutu-oksuz-nobeti-test.py
    python3 tools/kutu-oksuz-nobeti-test.py --mutasyon     # mutant KOPYAYA uygulanir
    python3 tools/kutu-oksuz-nobeti-test.py --tools <dizin> --sessiz   # (mutasyon ic kullanimi)
"""
import contextlib
import importlib.util
import inspect
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
DOSYALAR = ("kutu-oksuz-nobeti.py", "kutu-arsivle.py", "durum.py")

# --------------------------------------------------------------------------
# FIKSTURLER
# --------------------------------------------------------------------------
TEMIZ = """## 2026-10-01 10:00 — A blogu
A govdesi

---

## 2026-09-30 10:00 — B blogu
B govdesi
"""

# 26 Eyl vakasi: kutunun DIBINE basliksiz kapanis govdesi.
DIBE = TEMIZ + """
---

MaCiT kapanis govdesi (baslik dustu)
- madde 1
"""

IKI = TEMIZ + """
---

yetim govde bir

---

yetim govde iki
"""

ORTADA = """## 2026-10-01 10:00 — A blogu
A govdesi

---

ortadaki blogun basligi dustu
- madde

---

## 2026-09-30 10:00 — B blogu
B govdesi
"""

CIT = """## 2026-10-01 10:00 — A blogu
kod ornegi:
```text
---
## sahte baslik
```
son satir

---

## 2026-09-30 10:00 — B blogu
B govdesi
"""

# Citin icinde YALNIZ ayrac var (sahte baslik YOK): cit takibi bozulursa citin icindeki
# `---` blogu boler ve ikinci yari BASLIKSIZ kalir -> yanlis-pozitif. CIT'teki sahte `## `
# baslik bu bolunmeyi KURTARDIGI icin o fikstur tek basina bu hatayi yakalayamaz.
CIT_YALNIZ_AYRAC = """## 2026-10-01 10:00 — A blogu
kod ornegi:
```text
---
sadece metin
```
son satir

---

## 2026-09-30 10:00 — B blogu
B govdesi
"""

BOS_BOLUT = """## 2026-10-01 10:00 — A blogu
A govdesi

---

---

---

## 2026-09-30 10:00 — B blogu
B govdesi

---
"""

AYRACSIZ = """## 2026-10-01 10:00 — A blogu
A govdesi

## 2026-09-30 10:00 — B blogu
B govdesi
"""

FM_SAGLAM = """---
name: kutu
---
## 2026-10-01 10:00 — A blogu
A govdesi
"""

FM_YARIM = """---
name: kutu
## 2026-10-01 10:00 — A blogu
A govdesi
"""

# 100+ `## `-baslikli blok, `---`'suz — gercek kutunun bugunku yapisinin fiksturu.
# Tek satir govde: silinen bir `## ` basliginin etkisini TEK bolut ikip bir bolutta
# yakalayabilsin diye (her bolut = 1 baslik + 1 govde satiri). Elle liste YAZMA.
AYRACSIZ_TEMIZ = "\n".join(f"## block {i}\nbody {i}" for i in range(105))
# 105 blok × 2 satir = 210 satir. Ilk baslik silinince `body 0` bolutsuz (ilk bolut
# `## ` basliksiz, 1 govde satiri kaliyor) -> OKSUZ rc=1.
AYRACSIZ_BASLIK_DUSMUS = AYRACSIZ_TEMIZ.split("\n", 1)[1]


class Suite:
    def __init__(self):
        self.vaka = 0
        self.iddia = 0
        self.kirmizi = []

    def bekle(self, ad, kosul, ayrinti=""):
        self.iddia += 1
        if not kosul:
            self.kirmizi.append("%s :: %s" % (ad, ayrinti))


def yaz(yol, metin, ikili=False):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb" if ikili else "w", **({} if ikili else {"encoding": "utf-8"})) as f:
        f.write(metin)
    return yol


def satir_no(metin, parca):
    """`parca`yi iceren ilk satirin 1-indeksli numarasi."""
    for i, s in enumerate(metin.splitlines(), 1):
        if parca in s:
            return i
    raise AssertionError("fikstur parcasi yok: %r" % parca)


def bolut_basi(metin, parca):
    """`parca`yi iceren satirin BOLUTUNUN 1-indeksli bas satiri (kendinden onceki
    ayracin hemen sonrasi). `kutu-arsivle.oksuz_govdeler`in bildirdigi satir budur:
    ilk DOLU satir degil, bolutun basi."""
    satirlar = metin.splitlines()
    i = satir_no(metin, parca) - 1
    while i > 0 and not re.match(r"^-{3,}[ \t]*$", satirlar[i - 1]):
        i -= 1
    return i + 1


def cli(tools, *argv, env_ek=None):
    env = dict(os.environ)
    env.pop("PRUVO_KUTU_YOLU", None)
    env.update(env_ek or {})
    p = subprocess.run([sys.executable, os.path.join(tools, "kutu-oksuz-nobeti.py")]
                       + list(argv), capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr


def ilk_satir(cikti):
    s = cikti.splitlines()
    return s[0] if s else ""


def kutu_arsivle_kuru(tools, kutu, kok):
    """kutu-arsivle --kuru: kilit + arsiv fikstur dizininde (gercek HOME'a yazi YOK)."""
    arsiv = yaz(os.path.join(kok, "arsiv-fix.md"), "## 2026-01-01 — eski\nx\n")
    kilit = os.path.join(kok, ".kilit-fix.lock")
    p = subprocess.run([sys.executable, os.path.join(tools, "kutu-arsivle.py"), "--kuru",
                        "--kutu", kutu, "--arsiv", arsiv, "--kilit", kilit],
                       capture_output=True, text=True, timeout=120)
    return p.stdout + p.stderr


def kos(tools, ayrintili=True):
    s = Suite()
    kok = tempfile.mkdtemp(prefix="kutu-oksuz-test-")
    try:
        def p(ad, metin):
            return yaz(os.path.join(kok, ad, "kutu.md"), metin)

        def goster(ad, ek=""):
            if ayrintili:
                print("  ✅ %s %s" % (ad, ek))

        # ---- 1 temiz -----------------------------------------------------
        s.vaka += 1
        ad = "VAKA 1 temiz"
        rc, out, _ = cli(tools, "--kutu", p("v1", TEMIZ))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0", "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        s.bekle(ad, "HUKUM: YESIL (rc=0)" in out, out[-200:])
        goster(ad)

        # ---- 2 dibe basliksiz govde --------------------------------------
        s.vaka += 1
        ad = "VAKA 2 dibe basliksiz govde"
        rc, out, _ = cli(tools, "--kutu", p("v2", DIBE))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=1", "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 1, "rc=%d (n>0 KIRMIZI olmali)" % rc)
        beklenen = bolut_basi(DIBE, "MaCiT kapanis govdesi")
        s.bekle(ad, ("  ! KUTU %d. satir: BASLIKSIZ dolu bolut | MaCiT kapanis govdesi"
                     % beklenen) in out,
                "satir no %d bekleniyordu: %r" % (beklenen, out[-300:]))
        s.bekle(ad, "HUKUM: KIRMIZI (rc=1)" in out, out[-200:])
        s.bekle(ad, "NE YAPILMALI" in out, "onarim yolu basilmali")
        goster(ad, "(satir %d)" % beklenen)

        # ---- 3 iki oksuz -------------------------------------------------
        s.vaka += 1
        ad = "VAKA 3 iki oksuz govde"
        rc, out, _ = cli(tools, "--kutu", p("v3", IKI))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=2", "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 1, "rc=%d" % rc)
        goster(ad)

        # ---- 4 ortada ----------------------------------------------------
        s.vaka += 1
        ad = "VAKA 4 ortada basligi dusmus blok"
        rc, out, _ = cli(tools, "--kutu", p("v4", ORTADA))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=1", "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 1, "rc=%d" % rc)
        s.bekle(ad, ("  ! KUTU %d. satir:" % bolut_basi(ORTADA, "ortadaki blogun basligi")) in out,
                out[-300:])
        goster(ad)

        # ---- 5 cit icinde ------------------------------------------------
        s.vaka += 1
        ad = "VAKA 5 cit ici `---`/`## ` yanlis-pozitif YOK"
        for etiket, metin in (("sahte-baslikli", CIT), ("yalniz-ayracli", CIT_YALNIZ_AYRAC)):
            rc, out, _ = cli(tools, "--kutu", p("v5-" + etiket, metin))
            s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0",
                    "%s: ilk satir %r" % (etiket, ilk_satir(out)))
            s.bekle(ad, rc == 0, "%s: rc=%d" % (etiket, rc))
        goster(ad)

        # ---- 6 bos bolut -------------------------------------------------
        s.vaka += 1
        ad = "VAKA 6 ardisik ayrac / bos bolut"
        rc, out, _ = cli(tools, "--kutu", p("v6", BOS_BOLUT))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0", "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        goster(ad)

        # ---- 7 ayracsiz temiz (##-based sinir) -------------------------
        # Eski VAKA 7 (EKSEN_KOR rc=2) K424 takiple kalkti; gercek kutu `## ` headers
        # ile bolunuyor ve ayracsiz temiz kutu artik `n=0 rc=0` ile YESIL.
        s.vaka += 1
        ad = "VAKA 7 ayracsiz temiz kutu = ##-based YESIL"
        rc, out, _ = cli(tools, "--kutu", p("v7", AYRACSIZ))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0",
                "ayracsiz temiz kutu 0 basmali: %r" % ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        s.bekle(ad, "HUKUM: YESIL (rc=0)" in out, out[-200:])
        s.bekle(ad, "EKSEN_KOR" not in out,
                "ayracsiz temiz kutu EKSEN_KOR BASMAMALI (yeni yol): %r" % out[-300:])
        goster(ad)

        # ---- 8 dosya yok, dizin var --------------------------------------
        s.vaka += 1
        ad = "VAKA 8 dosya yok (dizin var)"
        os.makedirs(os.path.join(kok, "v8"))
        rc, out, _ = cli(tools, "--kutu", os.path.join(kok, "v8", "yok.md"))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=OLCULEMEDI", ilk_satir(out))
        s.bekle(ad, rc == 2, "rc=%d" % rc)
        goster(ad)

        # ---- 9 dizin de yok ----------------------------------------------
        s.vaka += 1
        ad = "VAKA 9 hafiza dizini yok (CI)"
        rc, out, _ = cli(tools, "--kutu", os.path.join(kok, "v9-yok-dizin", "kutu.md"))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=MAKINEDE_YOK", ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        goster(ad)

        # ---- 10 UTF-8 degil ----------------------------------------------
        s.vaka += 1
        ad = "VAKA 10 UTF-8 degil"
        yol = yaz(os.path.join(kok, "v10", "kutu.md"), b"\xff\xfe## x\n", ikili=True)
        rc, out, _ = cli(tools, "--kutu", yol)
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=OLCULEMEDI", ilk_satir(out))
        s.bekle(ad, rc == 2, "rc=%d" % rc)
        goster(ad)

        # ---- 11 yarim frontmatter ----------------------------------------
        s.vaka += 1
        ad = "VAKA 11 yarim frontmatter"
        rc, out, _ = cli(tools, "--kutu", p("v11", FM_YARIM))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=OLCULEMEDI", ilk_satir(out))
        s.bekle(ad, rc == 2, "rc=%d" % rc)
        goster(ad)

        # ---- 12 saglam frontmatter ---------------------------------------
        s.vaka += 1
        ad = "VAKA 12 saglam frontmatter"
        rc, out, _ = cli(tools, "--kutu", p("v12", FM_SAGLAM))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0", ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        goster(ad)

        # ---- 13 ikiz tanim kilidi ----------------------------------------
        s.vaka += 1
        ad = "VAKA 13 ikiz tanim kilidi (kutu-arsivle --kuru ile ESIT)"
        for etiket, metin, n_bekle in (("temiz", TEMIZ, 0), ("dibe", DIBE, 1),
                                       ("iki", IKI, 2), ("ortada", ORTADA, 1),
                                       ("cit", CIT, 0), ("cit2", CIT_YALNIZ_AYRAC, 0),
                                       ("bos", BOS_BOLUT, 0)):
            yol = p("v13-" + etiket, metin)
            _, out, _ = cli(tools, "--kutu", yol)
            benim = ilk_satir(out)
            kuru = kutu_arsivle_kuru(tools, yol, os.path.join(kok, "v13-" + etiket))
            m = re.search(r"oksuz_govde_kutu=(\d+)", kuru)
            s.bekle(ad, m is not None, "%s: kutu-arsivle --kuru oksuz_govde_kutu basmadi: %r"
                    % (etiket, kuru[-300:]))
            if m:
                s.bekle(ad, int(m.group(1)) == n_bekle,
                        "%s: kutu-arsivle %s, beklenen %d" % (etiket, m.group(1), n_bekle))
                s.bekle(ad, benim == "KUTU_OKSUZ_GOVDE=%s" % m.group(1),
                        "%s: benim %r != kutu-arsivle %s" % (etiket, benim, m.group(1)))
        yol = p("v13-ayracsiz", AYRACSIZ)
        kuru = kutu_arsivle_kuru(tools, yol, os.path.join(kok, "v13-ayracsiz"))
        s.bekle(ad, "EKSEN_KOR=oksuz_govde_kutu" in kuru,
                "ayracsiz kutuda kutu-arsivle EKSEN_KOR basmali: %r" % kuru[-300:])
        goster(ad)

        # ---- 14 --kutu degersiz ------------------------------------------
        s.vaka += 1
        ad = "VAKA 14 --kutu degersiz"
        rc, out, _ = cli(tools, "--kutu")
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=OLCULEMEDI", ilk_satir(out))
        s.bekle(ad, rc == 2, "rc=%d" % rc)
        goster(ad)

        # ---- 15 gercek kutu smoke (yazi YOK) -----------------------------
        s.vaka += 1
        ad = "VAKA 15 gercek kutu smoke (yalniz okur)"
        rc, out, _ = cli(tools)
        s.bekle(ad, re.fullmatch(r"KUTU_OKSUZ_GOVDE=(\d+|OLCULEMEDI|MAKINEDE_YOK)",
                                 ilk_satir(out)) is not None,
                "sozlesme satiri bicimi bozuk: %r" % ilk_satir(out))
        s.bekle(ad, rc in (0, 1, 2), "rc=%d" % rc)
        s.bekle(ad, (rc == 0) == (ilk_satir(out) in ("KUTU_OKSUZ_GOVDE=0",
                                                     "KUTU_OKSUZ_GOVDE=MAKINEDE_YOK")),
                "rc/sayi tutarsiz: rc=%d satir=%r" % (rc, ilk_satir(out)))
        goster(ad, "(%s rc=%d)" % (ilk_satir(out), rc))

        # ---- 16 durum.py baglantisi --------------------------------------
        s.vaka += 1
        ad = "VAKA 16 durum.py baglantisi"
        spec = importlib.util.spec_from_file_location(
            "durum_kutu_oksuz_test", os.path.join(tools, "durum.py"))
        dm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dm)
        kaynak = inspect.getsource(dm.main)
        s.bekle(ad, "_kutu_oksuz_satirlari()" in kaynak,
                "durum.main() bolum 10'u CAGIRMIYOR (olcum kolu panodan kopmus)")
        s.bekle(ad, "ORTAK KUTU BUTUNLUGU" in kaynak, "bolum 10 basligi main()'de yok")
        eski = os.environ.get("PRUVO_KUTU_YOLU")
        os.environ["PRUVO_KUTU_YOLU"] = p("v16", DIBE)
        try:
            satirlar = dm._kutu_oksuz_satirlari()
        finally:
            if eski is None:
                os.environ.pop("PRUVO_KUTU_YOLU", None)
            else:
                os.environ["PRUVO_KUTU_YOLU"] = eski
        govde = "\n".join(satirlar)
        s.bekle(ad, "🔴 KUTU_OKSUZ_GOVDE=1" in govde,
                "pano oksuz govdede KIRMIZI satir basmali: %r" % govde[:300])
        s.bekle(ad, ("satir %d" % bolut_basi(DIBE, "MaCiT kapanis govdesi")) in govde, govde[:300])
        goster(ad)

        # ---- 17 CLI girisi modulden SURULUR (sahipsiz-kapi SURULEN olcutu) -
        # Alt surec (VAKA 1-15) gercek kullanimi olcer; sahipsiz-kapi-nobetcisi ise
        # yalniz modulu YUKLEYIP giris fonksiyonunu `<modul>.main(...)` bicimiyle
        # cagiran surucuyu "surulen" sayar. Ayni iki hal (temiz / dibe oksuz) burada
        # main() uzerinden de olculur: CLI girisi ile alt surec ayrisirsa KIRMIZI.
        s.vaka += 1
        ad = "VAKA 17 main() modulden surulur"
        spec = importlib.util.spec_from_file_location(
            "kutu_oksuz_nobeti_surucu", os.path.join(tools, "kutu-oksuz-nobeti.py"))
        ko = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ko)
        for etiket, metin, n, beklenen_rc in (("v17a", TEMIZ, "0", 0), ("v17b", DIBE, "1", 1)):
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                rc = ko.main(["--kutu", p(etiket, metin)])
            out = tampon.getvalue()
            s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=" + n,
                    "%s: ilk satir %r" % (etiket, ilk_satir(out)))
            s.bekle(ad, rc == beklenen_rc, "%s: rc=%r" % (etiket, rc))
            rc_cli, out_cli, _ = cli(tools, "--kutu", p(etiket, metin))
            s.bekle(ad, (rc_cli, out_cli) == (rc, out),
                    "%s: main() ile alt surec AYRISTI" % etiket)
        goster(ad)

        # ---- 18 ayracsiz 100+ bloklu temiz (a) --------------------------
        # 105 `## `-baslikli blok, `---` yok -> yeni yol `## ` sinir ile TEMIZI
        # sayiyor (eski EKSEN_KOR rc=2 kalkti).
        s.vaka += 1
        ad = "VAKA 18 ayracsiz 100+ bloklu temiz = YESIL"
        rc, out, _ = cli(tools, "--kutu", p("v18", AYRACSIZ_TEMIZ))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=0",
                "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 0, "rc=%d" % rc)
        s.bekle(ad, "HUKUM: YESIL (rc=0)" in out, out[-200:])
        s.bekle(ad, "EKSEN_KOR" not in out,
                "yeni yol EKSEN_KOR BASMAMALI: %r" % out[-300:])
        blok_repr = re.search(r"blok=(\d+)", out)
        s.bekle(ad, blok_repr is not None and int(blok_repr.group(1)) == 105,
                "blok sayisi 105 olmali: %r" % out[-200:])
        goster(ad, "(105 blok)")

        # ---- 19 ayracsiz 100+ bloklu, ILK baslik silinmis (b) -----------
        # AYRACSIZ_TEMIZ'den `## block 0` satirini cikar -> ilk bolut basliksiz
        # kaliyor; yeni yol onu OKSUZ sayar.
        s.vaka += 1
        ad = "VAKA 19 ayracsiz 100+ bloklu, baslik dusmus = KIRMIZI"
        rc, out, _ = cli(tools, "--kutu", p("v19", AYRACSIZ_BASLIK_DUSMUS))
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=1",
                "ilk satir %r" % ilk_satir(out))
        s.bekle(ad, rc == 1, "rc=%d" % rc)
        s.bekle(ad, "HUKUM: KIRMIZI (rc=1)" in out, out[-200:])
        s.bekle(ad, ("  ! KUTU 1. satir: BASLIKSIZ dolu bolut | body 0") in out,
                "body 0 satir 1'de BASLIKSIZ olarak basmali: %r" % out[-300:])
        goster(ad)

        # ---- 20 okunamayan dosya (c) ------------------------------------
        # UTF-8 degil + dosya yok + dizin yok zaten VAKA 8/9/10'da; burada kapinin
        # AYNEN korundugunu `---`suz kutu yolunda da gormek icin AYRACSIZ dosyanin
        # UTF-8 olmayan ikizini okutuyoruz. Boylece (c) nin (a)/(b) ile ayni yolun
        # parcasi oldugu kanitlaniyor (yoksa VAKA 10'un kapsami farkli kalmis olurdu).
        s.vaka += 1
        ad = "VAKA 20 ayracsiz okunamayan = OLCULEMEDI"
        yol = yaz(os.path.join(kok, "v20", "kutu.md"),
                  b"\xff\xfe## block 0\nbody 0\n## block 1\n", ikili=True)
        rc, out, _ = cli(tools, "--kutu", yol)
        s.bekle(ad, ilk_satir(out) == "KUTU_OKSUZ_GOVDE=OLCULEMEDI", ilk_satir(out))
        s.bekle(ad, rc == 2, "rc=%d" % rc)
        s.bekle(ad, "UTF-8" in out, "UTF-8 sebebi basmali: %r" % out[-300:])
        goster(ad)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return s


# --------------------------------------------------------------------------
# MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosya DEGISMEZ
# --------------------------------------------------------------------------
# (ad, dosya, eski, yeni, oldurmeli)
MUTANTLAR = (
    ("M1 tespit tanimi bosaltilir (oksuz_govdeler daima bos)",
     "kutu-arsivle.py",
     "        if not dolu or baslik:\n            continue\n        ornek = \"\"",
     "        if True:\n            continue\n        ornek = \"\"", True),
    ("M2 n>0 halinde cikis kodu 0 (KIRMIZI yutulur)",
     "kutu-oksuz-nobeti.py",
     "    HAL_OKSUZ: RC_KIRMIZI,", "    HAL_OKSUZ: RC_TEMIZ,", True),
    ("M3 blok-basi turevimi `---`-yalniz'a geri (ayracsiz EKSEN_KOR rc=2 doner)",
     "kutu-oksuz-nobeti.py",
     "    elif ayrac == 0 and blok > 1:\n"
     "        # Ayracsiz kutu: ## headers'la bolut sinirini turet, basliksiz bolut varsa OKSUZ.\n"
     "        yerel = _yerel_ayracsiz_oksuz(m, satirlar, fm_son)\n"
     "        if yerel:\n"
     "            sonuc.update(n=len(yerel), ornekler=yerel)\n"
     "            sonuc[\"hal\"] = HAL_OKSUZ\n"
     "        else:\n"
     "            sonuc[\"n\"] = 0\n"
     "            sonuc[\"hal\"] = HAL_TEMIZ",
     "    elif ayrac == 0 and blok > 1:\n"
     "        sonuc[\"n\"] = None\n"
     "        sonuc[\"hata\"] = (\"kutuda ayrac (`---`) YOK ve %d blok var -> dusen baslik bu eksende YAPISAL OLARAK gorunmez (EKSEN_KOR)\" % blok)",
     True),
    ("M4 dosya YOK (dizin var) 'temiz' sayilir",
     "kutu-oksuz-nobeti.py",
     "        sonuc[\"hata\"] = \"kutu dosyasi YOK (hafiza dizini var): %s\" % yol\n"
     "        return sonuc",
     "        sonuc[\"hal\"] = HAL_TEMIZ\n        return sonuc", True),
    ("M5 sozlesme satiri adi degisir (KUTU_OKSUZ_GOVDE= basilmaz)",
     "kutu-oksuz-nobeti.py",
     "satirlar = [\"KUTU_OKSUZ_GOVDE=%s\" % _sayi_metni(s)]",
     "satirlar = [\"KUTU=%s\" % _sayi_metni(s)]", True),
    ("M6 'olculemedi' sayisi 0 basilir (0 ile olcemedim karisir)",
     "kutu-oksuz-nobeti.py",
     "    if s[\"n\"] is None:\n        return \"OLCULEMEDI\"",
     "    if s[\"n\"] is None:\n        return \"0\"", True),
    ("M7 yarim frontmatter fail-closed'u kalkar",
     "kutu-oksuz-nobeti.py",
     "    if fm_hata:", "    if False:", True),
    ("M8 hafiza dizini yok halinde rc=2 (CI'yi kirmizi yakar)",
     "kutu-oksuz-nobeti.py",
     "            sonuc[\"hal\"] = HAL_MAKINEDE_YOK\n            return sonuc",
     "            sonuc[\"hal\"] = HAL_OLCULEMEDI\n            return sonuc", True),
    ("M9 ornek satir numarasi 1 kayar",
     "kutu-oksuz-nobeti.py",
     "BASLIKSIZ dolu bolut | %s\" % (satir_no, ornek))",
     "BASLIKSIZ dolu bolut | %s\" % (satir_no + 1, ornek))", True),
    ("M10 pano bolumu 10 main()'den kopar (cagri silinir)",
     "durum.py",
     "        kutu_satirlari = _kutu_oksuz_satirlari()",
     "        kutu_satirlari = []", True),
    ("M11 cit disi ayrac tanimi bozulur (cit ici `---` bolut sayilir)",
     "kutu-arsivle.py",
     "        if FENCE_RE.match(s):\n            ic = not ic\n            dolu = True\n"
     "        elif ic:\n            if s.strip():\n                dolu = True\n"
     "        elif AYRAC_RE.match(s):",
     "        if FENCE_RE.match(s):\n            dolu = True\n"
     "        elif False:\n            if s.strip():\n                dolu = True\n"
     "        elif AYRAC_RE.match(s):", True),
    ("N1 ILGISIZ: yorum satiri eklenir",
     "kutu-oksuz-nobeti.py",
     "# Ekrana basilan ornek sayisi tavani",
     "# (ilgisiz mutasyon: davranis degismez)\n# Ekrana basilan ornek sayisi tavani", False),
)


def mutasyon_turu():
    print("MUTASYON TURU — mutant KOPYAYA uygulanir, canli dosyalar DEGISMEZ")
    import hashlib

    def sha(yol):
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    once = {d: sha(os.path.join(TOOLS, d)) for d in DOSYALAR}
    kirmizi = []
    for ad, dosya, eski, yeni, oldurmeli in MUTANTLAR:
        kaynak = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
        if kaynak.count(eski) != 1:
            kirmizi.append("%s :: DESEN %d KEZ BULUNDU (tam 1 olmali; mutant bayat/belirsiz) "
                           "-> %r" % (ad, kaynak.count(eski), eski[:60]))
            print("  🔴 %-66s DESEN %d" % (ad, kaynak.count(eski)))
            continue
        gecici = tempfile.mkdtemp(prefix="kutu-oksuz-mut-")
        try:
            for d in DOSYALAR:
                shutil.copy2(os.path.join(TOOLS, d), os.path.join(gecici, d))
            with open(os.path.join(gecici, dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--tools", gecici, "--sessiz"],
                               capture_output=True, text=True, timeout=900)
            olduruldu = p.returncode != 0
            tamam = (olduruldu == oldurmeli)
            print("  %s %-66s rc=%d (%s)" % ("✅" if tamam else "🔴", ad, p.returncode,
                                             "OLDU" if olduruldu else "YASIYOR"))
            if not tamam:
                kirmizi.append("%s :: beklenen %s, gelen %s | %s"
                               % (ad, "OLDU" if oldurmeli else "YASIYOR",
                                  "OLDU" if olduruldu else "YASIYOR",
                                  (p.stdout + p.stderr).strip()[-300:]))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    sonra = {d: sha(os.path.join(TOOLS, d)) for d in DOSYALAR}
    degisen = [d for d in DOSYALAR if once[d] != sonra[d]]
    print("\nCANLI DOSYALAR sha256: %s" % ("ESIT ✅" if not degisen else "DEGISMIS 🔴 %s" % degisen))
    if degisen:
        kirmizi.append("CANLI DOSYA DEGISMIS — mutant sizdi: %s" % degisen)
    print("\nMUTASYON SONUC: %d mutant, %d kirmizi" % (len(MUTANTLAR), len(kirmizi)))
    for k in kirmizi:
        print("  🔴 " + k)
    return 1 if kirmizi else 0


def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    if "--mutasyon" in argv:
        return mutasyon_turu()
    tools = TOOLS
    if "--tools" in argv:
        i = argv.index("--tools")
        if i + 1 >= len(argv):
            print("HATA: --tools bir dizin bekler", file=sys.stderr)
            return 2
        tools = argv[i + 1]
        del argv[i:i + 2]
    sessiz = "--sessiz" in argv
    bilinmeyen = [a for a in argv if a != "--sessiz"]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    if not sessiz:
        print("KUTU OKSUZ GOVDE NOBETCISI KABUL TESTI — tools: %s" % tools)
    try:
        s = kos(tools, ayrintili=not sessiz)
    except Exception as e:
        import traceback
        print("🔴 SUITE PATLADI (%s: %s)" % (type(e).__name__, e))
        if not sessiz:
            traceback.print_exc()
        return 1
    print("\n%d vaka, %d iddia, %d kirmizi" % (s.vaka, s.iddia, len(s.kirmizi)))
    for k in s.kirmizi:
        print("  🔴 " + k)
    print("SONUC: " + ("YESIL ✅" if not s.kirmizi else "KIRMIZI 🔴"))
    return 1 if s.kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
