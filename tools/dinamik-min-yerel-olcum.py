#!/usr/bin/env python3
"""YEREL OLCUM (CI DISI; uretec deposu ~/dev/pruvo-jenerator gerekir): DINAMIK ALT SINIR (BaBa 14:3x kabul listesi).

(1) TABLO: 24 turde surgu alt siniri manifestten (en_az; olcu_min_dinamik turde "dinamik") — beklenen 10 x serbest ·
    rolyef/topo/sehir 60 · yildiz 80 · ses/braille/koordinat dinamik.
(2) DINAMIK 3 TUR x 2 GIRDI (kisa/uzun): canli koşucunun AYNI yolu (esle_fonksiyonu -> kopru min-hesapla ->
    tekin_kos): min KISA < min UZUN; min'in adima yuvarlisinda uretec rc 0 + sizdirmaz; bir adim altinda koşucu
    `RED olcu-min-<N>` (uretec KOSMAZ).
Yazim: yalniz tempfile (silinir). D1/R2/canli YOK.
Cikti: satirlar + son satir `DINAMIK_MIN_YEREL tablo=<ok|sapma> tur=<k>/3 rc=<0|1|3>`.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEN = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
PY = os.environ.get("FOTO_KOSUCU_PYTHON") or "/opt/homebrew/bin/python3"

# bust = rolyef ureteci (teklif turu) -> rolyef tabani 60 (uretilemeyen olcu sunulmaz).
SABIT = {"rolyef": 60, "topo": 60, "sehir": 60, "yildiz": 80, "bust": 60}
# Turetilmis eksen (G4) surgu tasimaz; tabloda "turetilmis".
GENLIK = [round(0.2 + 0.8 * abs(((i * 37) % 100) - 50) / 50.0, 3) for i in range(400)]
GIRDI = {
    "ses": ({"genlik": GENLIK, "cubuk_sayisi": 40}, {"genlik": GENLIK, "cubuk_sayisi": 100}),
    "braille": ({"metin": "ab"}, {"metin": "abcdefghij"}),
    "koordinat": ({"enlem": 41.0082, "boylam": 28.9784},
                  {"enlem": 41.0082, "boylam": 28.9784, "serbest_metin": "Istanbul Bogazi"}),
}


def modul(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def main():
    kos = modul("foto_uretec_kosucu", os.path.join(KOK, "tools", "foto-uretec-kosucu.py"))
    turler = kos.manifest_oku()
    sapma = []
    for kod, t in turler.items():
        a = (t.get("olcu_mm") or {}).get("en_az")
        if t.get("olcu_min_dinamik") is True:
            deger = "dinamik"
        elif kos.turetilmis(t):
            deger = "turetilmis"
        else:
            deger = a
            if a != SABIT.get(kod, 10):
                sapma.append("%s=%s (beklenen %s)" % (kod, a, SABIT.get(kod, 10)))
        print("TABLO %-10s alt=%s" % (kod, deger))
    print("TABLO_SAPMA=%d %s" % (len(sapma), " ".join(sapma)))
    if not os.path.isdir(JEN):
        print("DINAMIK_MIN_YEREL=OLCULEMEDI uretec-deposu-yok yol=%s rc=3" % JEN)
        return 3
    tutan = 0
    for kod, (kisa, uzun) in GIRDI.items():
        t = turler[kod]
        cli = kos.cli_tablosu().get(t.get("uretec"))
        adim = (t.get("fiyat") or {}).get("adim_mm") or 10
        sonuc = []
        for ad, p in (("kisa", kisa), ("uzun", uzun)):
            d = tempfile.mkdtemp(prefix="dmin-")
            try:
                g = {"tur": kod, "olcu_mm": 100.0, "parametreler": p, "dosyalar": {}, "renkler": {}}
                u, _ = kos.esle_fonksiyonu(t, cli)(g, d, kos.renk_tablosu())
                ug = os.path.join(d, "u.json")
                with open(ug, "w", encoding="utf-8") as f:
                    json.dump(u, f)
                mn = kos.min_hesapla(PY, JEN, kod, ug)
                if mn is None:
                    import subprocess
                    p = subprocess.run([PY, os.path.join(JEN, "jeneratorler", "kopru", "kopru_uret.py"), "min-hesapla",
                                        "--kategori", kod, "--girdi-mh", ug], capture_output=True, text=True, cwd=JEN)
                    print("TESHIS %s %s min-hesapla rc=%d err=%s out=%s" % (
                        kod, ad, p.returncode, p.stderr.strip()[-300:], p.stdout.strip()[-200:]))
                    sonuc.append((ad, None, None, None))
                    continue
                n = kos.min_adim(t, mn)

                def kos_olcu(olcu):
                    gd, cikti = os.path.join(d, "g%d" % olcu), os.path.join(d, "c%d" % olcu)
                    os.makedirs(gd)
                    with open(os.path.join(gd, "girdi.json"), "w", encoding="utf-8") as f:
                        json.dump({"sozlesme": 1, "kategori": kod, "siparis_no": "YEREL", "kalem": 0, "olcu_mm": olcu,
                                   "renkler": {}, "malzemeler": {}, "parametreler": p, "dosyalar": {}}, f)
                    rc, ozet = kos.tekin_kos(cli, t, gd, cikti, PY, JEN)
                    o = {}
                    if rc == 0 and os.path.isfile(os.path.join(cikti, "olcu.json")):
                        with open(os.path.join(cikti, "olcu.json"), encoding="utf-8") as f:
                            o = json.load(f)
                    return rc, ozet, o

                rc1, oz1, o1 = kos_olcu(n)
                rc0, oz0, _ = kos_olcu(n - adim)
                if rc1 != 0:
                    print("TESHIS %s %s olcu=%s rc=%d ozet=%s" % (kod, ad, n, rc1, oz1))
                sonuc.append((ad, mn, (rc1, o1.get("sizdirmaz"), o1.get("min_mm")), (rc0, oz0)))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        ok = all(s[1] is not None for s in sonuc) and sonuc[0][1] < sonuc[1][1]
        for ad, mn, ust, alt in sonuc:
            ust_ok = ust is not None and ust[0] == 0 and ust[1] is True and ust[2] == mn
            alt_ok = alt is not None and alt[0] == 2 and "olcu-min-" in (alt[1] or "")
            ok = ok and ust_ok and alt_ok
            print("DINAMIK %-9s %-4s min=%s ust(rc,sizdirmaz,min_mm)=%s alt=%s" % (kod, ad, mn, ust, alt))
        tutan += 1 if ok else 0
        print("DINAMIK %-9s HAL=%s" % (kod, "TUTTU" if ok else "TUTMADI"))
    rc = 0 if tutan == len(GIRDI) and not sapma else 1
    print("DINAMIK_MIN_YEREL tablo=%s tur=%d/%d rc=%d" % ("ok" if not sapma else "sapma", tutan, len(GIRDI), rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
