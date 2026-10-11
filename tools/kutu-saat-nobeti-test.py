#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kutu-saat-nobeti.py KABUL + MUTANT BATARYASI — HERMETIK.

    python3 tools/kutu-saat-nobeti-test.py              # vakalar
    python3 tools/kutu-saat-nobeti-test.py --mutasyon   # vakalar + mutantlar

Fikstur kutulari tempfile dizininde; gercek kutuya / gercek HOME'a YAZILMAZ, her koşumda
`--kutu` ve `--simdi` acikca verilir. Mutantlar aracin IZOLE kopyasinda (tempfile) uretilir;
CANLI dosya yamanmaz. Yardimci `kutu-arsivle.py` de kopyaya yanina konur (arac onu kendi
dizininden yukler). Capasi bulunmayan mutant YASADI sayilir (sessiz gecis yok).

Her vaka `VAKA=<ad> SONUC=GECTI|KALDI`; son satir `KABUL=GECTI|KALDI (...)`, rc 0 yalniz GECTI.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "kutu-saat-nobeti.py")
YARDIMCI = os.path.join(TOOLS, "kutu-arsivle.py")

MUTANTLAR = (
    ("m1-ihlal-sayilmaz", "if an > simdi:", "if False:"),
    ("m2-x-ust-sinir", '(0 if birler in "xX"', '(9 if birler in "xX"'),
)


def _kos(arac, args):
    p = subprocess.run([sys.executable, arac] + args, capture_output=True, text=True,
                       timeout=60)
    return p.returncode, p.stdout.splitlines()


def _kutu(dizin, ad, metin):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return yol


def vakalar(arac, dizin):
    """[(ad, gecti_mi, ayrinti)]"""
    sonuc = []

    def vaka(ad, kutu_metni, simdi, beklenen_n, beklenen_rc, ek=None):
        yol = _kutu(dizin, ad + ".md", kutu_metni) if kutu_metni is not None else \
            os.path.join(dizin, "yok-" + ad + ".md")
        rc, cikti = _kos(arac, ["--kutu", yol, "--simdi", simdi])
        ilk = cikti[0] if cikti else ""
        ok = rc == beklenen_rc and ilk == "KUTU_ILERI_SAAT=%s" % beklenen_n
        ileri = [c for c in cikti if c.startswith("ILERI ")]
        if isinstance(beklenen_n, int):
            ok = ok and len(ileri) == beklenen_n
        if ek is not None:
            ok = ok and ek(cikti)
        sonuc.append((ad, ok, "rc=%s ilk=%s" % (rc, ilk)))

    temiz = ("## 2026-10-11 01:0x — ▶️ KraL acilis\nmetin\n\n"
             "## 2026-10-11 00:58 — ✅ MaCiT kapanis\nmetin\n")
    vaka("a-temiz", temiz, "2026-10-11 01:03", 0, 0,
         lambda c: c[-1] == "AYRISMAYAN=0")
    vaka("b-2x-ileri-tekin", "## 2026-10-11 01:2x — 📊 TeKiN → BaBa olcum\n", "2026-10-11 01:03",
         1, 1, lambda c: any("ev=TeKiN" in s and "fark_dk=17" in s and "satir=1" in s
                             for s in c))
    vaka("c-0x-ayni-dilim", "## 2026-10-11 01:0x(b) — ▶️ BaBa\n", "2026-10-11 01:03", 0, 0)
    vaka("d1-dakika-ileri", "## 2026-10-11 01:04 — KraL\n", "2026-10-11 01:03", 1, 1)
    vaka("d2-dakika-esit", "## 2026-10-11 01:03 — KraL\n", "2026-10-11 01:03", 0, 0)
    vaka("e1-gece-yarisi-ileri", "## 2026-10-12 00:0x — ArTisT\n", "2026-10-11 23:59", 1, 1,
         lambda c: any("ev=ArTisT" in s and "fark_dk=1 " in s for s in c))
    vaka("e2-gece-yarisi-geri", "## 2026-10-11 23:5x — ArTisT\n", "2026-10-12 00:10", 0, 0)
    citli = ("## 2026-10-11 01:00 — KraL\n```\n## 2026-10-11 09:9x — TeKiN cit ici\n"
             "## 2026-10-11 05:00 — TeKiN cit ici\n```\n")
    vaka("f-cit-ici-sayilmaz", citli, "2026-10-11 01:03", 0, 0,
         lambda c: c[-1] == "AYRISMAYAN=0")
    vaka("g-bilinmeyen-ev", "## 2026-10-11 02:00 — ✅ Yabanci kapanis\n", "2026-10-11 01:03",
         1, 1, lambda c: any("ev=BILINMIYOR" in s for s in c))
    vaka("h-dosya-yok", None, "2026-10-11 01:03", "OLCULEMEDI", 2,
         lambda c: not any(s.startswith("KUTU_ILERI_SAAT=0") for s in c))
    # (i) bozuk --simdi
    yol = _kutu(dizin, "i.md", temiz)
    rc, cikti = _kos(arac, ["--kutu", yol, "--simdi", "2026-13-40 25:61"])
    sonuc.append(("i-bozuk-simdi", rc == 2 and cikti[:1] == ["KUTU_ILERI_SAAT=OLCULEMEDI"],
                  "rc=%s" % rc))
    vaka("j-ayrismayan", "## Baslik saatsiz — KraL\n\n## 2026-10-11 01:00 — KraL\n",
         "2026-10-11 01:03", 0, 0, lambda c: c[-1] == "AYRISMAYAN=1")
    # (k) kutu dizini yok -> MAKINEDE_YOK rc0 (0 BASILMAZ)
    rc, cikti = _kos(arac, ["--kutu", os.path.join(dizin, "olmayan-dizin", "k.md"),
                            "--simdi", "2026-10-11 01:03"])
    sonuc.append(("k-makinede-yok", rc == 0 and cikti[:1] == ["KUTU_ILERI_SAAT=MAKINEDE_YOK"],
                  "rc=%s" % rc))
    # (l) UTF-8 olmayan dosya -> OLCULEMEDI rc2
    yol = os.path.join(dizin, "l.md")
    with open(yol, "wb") as f:
        f.write(b"## 2026-10-11 01:00 \xff\xfe\n")
    rc, cikti = _kos(arac, ["--kutu", yol, "--simdi", "2026-10-11 01:03"])
    sonuc.append(("l-utf8-degil", rc == 2 and cikti[:1] == ["KUTU_ILERI_SAAT=OLCULEMEDI"],
                  "rc=%s" % rc))
    # (m) CLI girisi modulden SURULUR (sahipsiz-kapi SURULEN olcutu; kardes
    # kutu-oksuz-nobeti-test VAKA 17 emsali): arac yuklenip `ks.main([...])` FIILEN
    # cagrilir; rc ve cikti alt surecle ESIT olmali (temiz -> 0/rc0, ileri -> 1/rc1).
    m_ok, m_ayrinti = True, []
    try:
        spec = importlib.util.spec_from_file_location("kutu_saat_nobeti_m", arac)
        ks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ks)
        for etiket, metin, beklenen in (("m-temiz", temiz, 0),
                                        ("m-ileri", "## 2026-10-11 01:2x — TeKiN\n", 1)):
            yol = _kutu(dizin, etiket + ".md", metin)
            args = ["--kutu", yol, "--simdi", "2026-10-11 01:03"]
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                mrc = ks.main(args)
            alt_rc, alt_cikti = _kos(arac, args)
            esit = mrc == alt_rc == beklenen and tampon.getvalue().splitlines() == alt_cikti
            m_ok = m_ok and esit
            m_ayrinti.append("%s:main=%s alt=%s" % (etiket, mrc, alt_rc))
    except Exception as e:  # yukleme/cagri kirildi -> KALDI (sessiz gecis yok)
        m_ok, m_ayrinti = False, ["hata=%s" % type(e).__name__]
    sonuc.append(("m-main-modulden-surulur", m_ok, " ".join(m_ayrinti)))
    return sonuc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    mutasyon = "--mutasyon" in argv
    with tempfile.TemporaryDirectory(prefix="kutu-saat-test-") as tmp:
        fikstur = os.path.join(tmp, "fikstur")
        os.mkdir(fikstur)
        canli = vakalar(ARAC, fikstur)
        for ad, ok, ayr in canli:
            print("VAKA=%s SONUC=%s%s" % (ad, "GECTI" if ok else "KALDI",
                                          "" if ok else "  (%s)" % ayr))
        v = sum(1 for _, ok, _ in canli if ok)
        V = len(canli)
        olen = 0
        if mutasyon:
            with open(ARAC, encoding="utf-8") as f:
                kaynak = f.read()
            for ad, capa, yerine in MUTANTLAR:
                mdizin = os.path.join(tmp, "mutant-" + ad)
                os.mkdir(mdizin)
                if kaynak.count(capa) != 1:
                    print("MUTANT=%s SONUC=YASADI (capa bulunamadi/tekil degil: %r)"
                          % (ad, capa))
                    continue
                with open(os.path.join(mdizin, "kutu-saat-nobeti.py"), "w",
                          encoding="utf-8") as f:
                    f.write(kaynak.replace(capa, yerine))
                shutil.copy(YARDIMCI, os.path.join(mdizin, "kutu-arsivle.py"))
                mfik = os.path.join(mdizin, "fikstur")
                os.mkdir(mfik)
                msonuc = vakalar(os.path.join(mdizin, "kutu-saat-nobeti.py"), mfik)
                kirmizi = [a for a, ok, _ in msonuc if not ok]
                if kirmizi:
                    olen += 1
                    print("MUTANT=%s SONUC=OLDU (kirmizi: %s)" % (ad, ",".join(kirmizi)))
                else:
                    print("MUTANT=%s SONUC=YASADI (hicbir vaka kirmizi yanmadi)" % ad)
    gecti = v == V and (not mutasyon or olen == len(MUTANTLAR))
    ek = ", %d/%d mutant oldu" % (olen, len(MUTANTLAR)) if mutasyon else ""
    print("KABUL=%s (%d/%d vaka%s)" % ("GECTI" if gecti else "KALDI", v, V, ek))
    return 0 if gecti else 1


if __name__ == "__main__":
    sys.exit(main())
