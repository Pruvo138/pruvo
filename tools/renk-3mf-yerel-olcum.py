#!/usr/bin/env python3
"""YEREL OLCUM (CI DISI; uretec deposu ~/dev/pruvo-jenerator gerekir): ODENEN RENK = 3MF EXTRUDER SAYISI.

BaBa 8 Eki 16:0x kabul satiri "yerel 3MF extruder=2 3 turde": 2 renk ucreti alinan siparisin girdisi
(tools/foto-uretec-kosucu.py tekin_kos — canli koşucunun AYNI yolu: esle -> gercek uretec -> §3 donusumu)
GERCEK uretecle uretilir; 3MF'teki farkli extruder sayisi (uc_mf_extruder_sayisi, olcu.json renk_sayisi) == 2
VE olcu.json parcalarinda iki bolge secilen renk adini tasir. Tek renk kontrolu: bust 1 renk -> extruder 1.

Turler: qr (plaka+kod) · isimlik (plaka+yazi) · bust (palet 2 renk -> taban+rolyef; iki_renk zorlanir).
Yazim: yalniz tempfile dizini (try/finally silinir). D1/R2/canli YOK.
Cikti: tur basina `YEREL_3MF <tur> renk=<n> extruder=<m> parcalar=<...> HAL=TUTTU|TUTMADI` + son satir
`YEREL_3MF_TUTAN=<k>/<n> rc=<0|1|3>` (3 = uretec deposu yok -> OLCULEMEDI).
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


def gri_png(yol, en=96, boy=96):
    """Gecerli 8 bit gri PNG (radyal tepe) — rolyef ureteci gercek gorsel ister (sahte imza RED gorsel)."""
    import struct
    import zlib
    ham = b"".join(b"\x00" + bytes(max(0, 255 - int(((x - en / 2) ** 2 + (y - boy / 2) ** 2) ** 0.5 * 5))
                                   for x in range(en)) for y in range(boy))
    def parca(tip, veri):
        return struct.pack(">I", len(veri)) + tip + veri + struct.pack(">I", zlib.crc32(tip + veri) & 0xFFFFFFFF)
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", en, boy, 8, 0, 0, 0, 0)) +
                parca(b"IDAT", zlib.compress(ham)) + parca(b"IEND", b""))


def modul(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


# (tur, renk adlari) — renk sayisi = odenen renk sayisi.
VAKALAR = [("qr", {"plaka": "Beyaz", "kod": "Siyah"}),
           ("isimlik", {"plaka": "Beyaz", "yazi": "Lacivert"}),
           ("bust", ["Gri", "Kırmızı"]),
           ("bust", ["Gri"])]


def main():
    if not os.path.isdir(JEN):
        print("YEREL_3MF=OLCULEMEDI uretec-deposu-yok yol=%s rc=3" % JEN)
        return 3
    kos = modul("foto_uretec_kosucu", os.path.join(KOK, "tools", "foto-uretec-kosucu.py"))
    esle = modul("kopru_esle_kapisi_test", os.path.join(KOK, "tools", "kopru-esle-kapisi-test.py"))
    man = os.path.join(KOK, "foto-uretim-veri.js")
    turler = kos.manifest_oku()
    _, deger, _ = esle.s_katmani(man, sorted({v[0] for v in VAKALAR}))
    tutan = 0
    for tur, renk in VAKALAR:
        t = turler[tur]
        palet = t.get("palet_bolgeleri") or []
        renkler = dict(zip(palet, renk)) if isinstance(renk, list) else dict(renk)
        n = len(set(renkler.values()))
        d = tempfile.mkdtemp(prefix="renk-3mf-")
        try:
            gd, cikti = os.path.join(d, "girdi"), os.path.join(d, "cikti")
            os.makedirs(gd)
            g = {"sozlesme": 1, "kategori": tur, "siparis_no": "YEREL", "kalem": 0,
                 "olcu_mm": (t.get("olcu_mm") or {}).get("en_cok") or 100, "renkler": renkler, "malzemeler": {},
                 "parametreler": deger.get(tur) or {}, "dosyalar": esle._dosyalar(gd)}
            gri_png(os.path.join(gd, g["dosyalar"]["foto"]))
            with open(os.path.join(gd, "girdi.json"), "w", encoding="utf-8") as f:
                json.dump(g, f, ensure_ascii=False)
            cli = kos.cli_tablosu().get(t.get("uretec"))
            rc, ozet = kos.tekin_kos(cli, t, gd, cikti, PY, JEN)
            olcu = {}
            if rc == 0 and os.path.isfile(os.path.join(cikti, "olcu.json")):
                with open(os.path.join(cikti, "olcu.json"), encoding="utf-8") as f:
                    olcu = json.load(f)
            ext = kos.uc_mf_extruder_sayisi(os.path.join(cikti, "model.3mf")) if rc == 0 else 0
            par = olcu.get("parcalar") or []
            par_ok = sorted(p.get("renk") for p in par) == sorted(renkler.values())
            ok = rc == 0 and ext == n and olcu.get("renk_sayisi") == n and par_ok
            tutan += 1 if ok else 0
            print("YEREL_3MF %-8s renk=%d extruder=%d parcalar=%s HAL=%s%s" % (
                tur, n, ext, ",".join("%s:%s" % (p.get("ad"), p.get("renk")) for p in par),
                "TUTTU" if ok else "TUTMADI", "" if rc == 0 else " rc=%d %s" % (rc, ozet)))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    rc = 0 if tutan == len(VAKALAR) else 1
    print("YEREL_3MF_TUTAN=%d/%d rc=%d" % (tutan, len(VAKALAR), rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
