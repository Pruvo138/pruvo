#!/usr/bin/env python3
"""FOTO URETEC KOSUCUSU — hermetik kabul testi + mutantlar (tools/foto-uretec-kosucu.py).

HERMETIK: wrangler yerine SAHTE komut (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici
dizin), uretec yerine SAHTE komut. Gercek D1/R2/ev yolu YOK; her sey tempfile altinda, bitince silinir.

Vakalar: T1 BOS rc=1 · T2 1 is -> ISLEDI + hazir + 3 dosya R2'de · T3 rc 2 -> elle · T4 ariza x3 -> elle ·
T5 sizdirmaz:false -> elle, R2 yazimi 0 · T6 CAS kaybi -> yazim yok · T7 D1/R2 erisim yok ->
OLCULEMEDI rc=4 + satir DEGISMEDI · T8 kilit -> KILITLI rc=3 · T9 KURU -> yazim 0 · T10 onizleme kuyrugu
-> onizleme-hazir · T11 log tavani · T12 KOPYA KOLU (onizlemeye bagli siparis, ayni girdi sha -> uretec
KOSMAZ, model onizlemeninki) · T12b sha farkli -> uretec yeniden koşar.
Mutantlar (kosucu kopyasi gecici dizinde): M1 sizdirmaz dogrulamasi silindi -> T5 KIRMIZI ·
M2 KURU kapisi silindi -> T9 · M3 CAS kira kontrolu silindi -> T6 · M4 deneme tavani yok -> T4 ·
M5 erisim hatasinda jeton geri verilmez -> T7 · M0 yorum -> 0 kirmizi.

G2 TEKIN-ORTAK KOPRUSU (7 Eki 2026): T13-<kod> (6 kategori) sahte tekin uretecine giden JSON BIREBIR
beklenen (olcu alani + RENK_HEX + secim eslemesi) + onizleme-hazir + olcu.json (renk_sayisi 3MF'ten,
girdi_sha256 damgali, onizleme >= 1024) · T14 RET "kontrast" -> hata `uretec-red:kontrast` ·
T15 kisa kenar > uzun -> uretec KOSMAZ · T16 tanimsiz renk adi -> uretec KOSMAZ · T17 renk_sayisi
3MF'ten OLCULUR (3 extruder) · T18 sema disi parametre -> uretec KOSMAZ.
Mutantlar: M8 renk eslemesi bozuk · M9 qr olcu alani yanlis · M10 muhur olcu alani yanlis ·
M11 kontrast kalibi yok · M12 renk_sayisi olculmez · M13 sema disi parametre kapisi yok.
Manifest tutarliligi (V1-V9, node + kopru modulu): 6 satir, metinler AYNEN, renk adlari RENK_HEX'te,
form alanlari uretec semasina eslenir, hak kutusu, red metni, parametre dogrulamasi.
`--gercek [--json <yol>]`: CI DISI — 6 GERCEK uretec x min/orta/maks = 18 koşum (sahte D1/R2).

`--uctan-uca`: CI DISI yerel prova — ayni sahte D1/R2 ile GERCEK litofan_uret.py (pruvo-jenerator,
salt okunur) kosulur; 3MF sizdirmaz + uzun kenar ±%1 + asama 'hazir' olculur.
"""
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
import re

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSUCU = os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
IS = "0123456789abcdef0123456789abcdef"
IS2 = "fedcba9876543210fedcba9876543210"
SIP = "PR-251007-101500-ABC"
GUNCEL0 = "2026-10-07T00:00:00.000Z"

SAHTE_WRANGLER = r'''
import json, os, shutil, sqlite3, sys
a = sys.argv[1:]
log = open(os.environ["FAKE_LOG"], "a")
log.write(json.dumps(a) + "\n"); log.close()
if a[:2] == ["d1", "execute"]:
    if os.environ.get("FAKE_D1_KAPALI"):
        sys.stderr.write("fetch failed\n"); sys.exit(1)
    sql = a[a.index("--command") + 1]
    c = sqlite3.connect(os.environ["FAKE_DB"]); c.row_factory = sqlite3.Row
    if os.environ.get("FAKE_CAS_KAYBI") and sql.startswith("UPDATE") and "uretec-bekliyor" in sql:
        c.execute("UPDATE foto_uretim SET asama='hazir', guncel='baska-kosucu'"); c.commit()
    cur = c.execute(sql); rows = [dict(r) for r in cur.fetchall()]; c.commit()
    print(json.dumps([{"results": rows, "success": True, "meta": {"changes": cur.rowcount if sql.startswith("UPDATE") else 0}}]))
    sys.exit(0)
if a[:2] == ["r2", "object"]:
    if os.environ.get("FAKE_R2_KAPALI"):
        sys.stderr.write("Authentication error\n"); sys.exit(1)
    anahtar = a[3].split("/", 1)[1]; dosya = a[a.index("--file") + 1]
    yol = os.path.join(os.environ["FAKE_R2"], anahtar)
    if a[2] == "get":
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist.\n"); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    os.makedirs(os.path.dirname(yol), exist_ok=True); shutil.copyfile(dosya, yol); sys.exit(0)
sys.exit(9)
'''

# Sahte 3MF onarim koprusu (TeKiN uc_mf_onar.py CLI: `<girdi> <cikti>` · `--olc <girdi> <cikti>`).
# FAKE_KOPRU: ok (varsayilan) | olc-kirmizi (her --olc rc 1 + kusur) | tek-kirmizi (yalniz TEK dosya --olc
# kirmizi; onarim sonrasi cift olcum gecer) | girdi (onarim rc 2).
SAHTE_KOPRU = r'''
import json, os, shutil, sys
a = sys.argv[1:]; mod = os.environ.get("FAKE_KOPRU", "ok")
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["kopru"] + a[:1]) + "\n")
if a and a[0] == "--olc":
    k = ["acik_kenar=3"] if mod == "olc-kirmizi" or (mod == "tek-kirmizi" and len(a) == 2) else []
    print(json.dumps({"kabul_kusurlari": k})); sys.exit(1 if k else 0)
if mod == "girdi":
    sys.stderr.write("GIRDI HATASI: sahte\n"); sys.exit(2)
shutil.copyfile(a[0], a[1]); open(a[1], "ab").write(b"ONARILDI"); sys.exit(0)
'''
HAM_3MF = b"PK\x03\x04HAM"

# Sahte tekin-ortak ureteci (G1/G2 CLI: --girdi <uretec json> --cikti <dizin> -> uretec.3mf + onizleme.png
# + ozet.json). Aldigi JSON'u FAKE_TEKIN_LOG'a yazar; extruder sayisi = girdideki renk alani sayisi
# (FAKE_TEKIN_EXTRUDER zorlar). FAKE_TEKIN_RET dolu -> stderr "RET: <metin>" rc 2.
SAHTE_TEKIN = r'''
import json, os, struct, sys, zipfile, zlib
a = sys.argv[1:]; g = json.load(open(a[a.index("--girdi") + 1], encoding="utf-8")); c = a[a.index("--cikti") + 1]
open(os.environ["FAKE_TEKIN_LOG"], "a", encoding="utf-8").write(json.dumps(g, ensure_ascii=False, sort_keys=True) + "\n")
if os.environ.get("FAKE_TEKIN_RET"):
    sys.stderr.write("RET: " + os.environ["FAKE_TEKIN_RET"] + "\n"); sys.exit(2)
L = 0.0
# G4 (kopru-15) olcu alanlari en_mm/dis_cap_mm/cap_mm/boru_cap_mm/u_aralik_mm/yukseklik_mm;
# onceki G2/S2 anahtarlari ONCE denenir (geriye uyumlu). dugme+saksi cap_mm; klips alt_ture gore
# boru_cap_mm / u_aralik_mm / yukseklik_mm.
for k in ("genislik_mm", "plaket_mm", "uzun_kenar_mm", "yuz_mm", "en_mm", "dis_cap_mm",
          "cap_mm", "boru_cap_mm", "u_aralik_mm", "yukseklik_mm"):
    if isinstance(g.get(k), (int, float)):
        L = float(g[k]); break
n = int(os.environ.get("FAKE_TEKIN_EXTRUDER") or 0) or max(1, len([k for k in g if k.startswith("renk")]))
os.makedirs(c)
ms = "<config>" + "".join('<part id="%d"><metadata key="extruder" value="%d"/></part>' % (i + 1, i + 1) for i in range(n)) + "</config>"
G = L * float(os.environ.get("FAKE_TEKIN_GEO") or 1.0)
vx = "".join('<vertex x="%g" y="%g" z="%g"/>' % (x, y, zz) for x in (0, G) for y in (0, G * 0.5) for zz in (0, 3))
with zipfile.ZipFile(os.path.join(c, "uretec.3mf"), "w") as z:
    z.writestr("3D/3dmodel.model", '<model unit="millimeter"><resources><object id="1" name="govde" type="model">'
               '<mesh><vertices>' + vx + '</vertices></mesh></object></resources><build><item objectid="1"/></build></model>')
    z.writestr("Metadata/model_settings.config", ms)
def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
ham = b"".join(b"\0" + b"\x80" * 1100 for _ in range(4))
open(os.path.join(c, "onizleme.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1100, 4, 8, 0, 0, 0, 0)) + ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b""))
oz = {"surum": "sahte", "sizdirmaz": True, "olcu_mm": [float(os.environ.get("FAKE_TEKIN_KUTU") or L), round(L * 0.5, 3), 3.0], "ucgen_sayisi": 24,
      "hacim_mm3": {"a": 1000.0, "toplam": 1000.0}}
if "genislik_mm" not in g and "plaket_mm" not in g:
    oz["uzun_kenar_mm"] = L  # NOMINAL; kosucu uzun kenari 3MF geometrisinden olcer (FAKE_TEKIN_GEO)
json.dump(oz, open(os.path.join(c, "ozet.json"), "w"))
'''

TEKIN_ESLE = {"isimlik_uret": "isimlik", "qr_plaket_uret": "qr", "svg_ekstruzyon_uret": "logo",
              "muhur_uret": "muhur", "siluet_sablon_uret": "sablon", "yapboz_uret": "yapboz",
              "ozel_uret:kutu": "kutu", "ozel_uret:adaptor": "adaptor",
              "ozel_uret:disli": "disli", "ozel_uret:kapak": "kapak",
              "ozel_uret:dugme": "dugme", "ozel_uret:klips": "klips", "ozel_uret:saksi": "saksi",
              "koordinat_uret": "koordinat"}
TUR_URETEC = {v: k for k, v in TEKIN_ESLE.items()}
SVG_ORNEK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><path fill-rule="evenodd" '
             'd="M0 0 H100 V60 H0 Z M15 30 A15 15 0 1 0 45 30 A15 15 0 1 0 15 30 Z M60 10 L90 30 L60 50 Z"/></svg>')

SAHTE_URETEC = r'''
import json, os, struct, sys, zlib
a = sys.argv[1:]; g = json.load(open(a[a.index("--girdi") + 1])); c = a[a.index("--cikti") + 1]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["uretec"]) + "\n")
mod = os.environ.get("FAKE_URETEC_MOD", "ok")
if mod == "red":
    sys.stderr.write("RED olcu-aralik: sahte\n"); sys.exit(2)
if mod == "ariza":
    sys.stderr.write("HATA: sahte ariza\n"); sys.exit(1)
os.makedirs(c)
open(os.path.join(c, "model.3mf"), "wb").write(b"PK\x03\x04" + b"\0" * 40)
def png(w, h):
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ham = b"".join(b"\0" + b"\x80" * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b"")
open(os.path.join(c, "onizleme.png"), "wb").write(png(1200, 4))
o = {"sozlesme": 1, "kategori": g["kategori"], "uzun_kenar_mm": float(g["olcu_mm"]),
     "kutu_mm": {"x": float(g["olcu_mm"]), "y": 100.0, "z": 3.0}, "renk_sayisi": 2,
     "sizdirmaz": mod != "sizdirmaz", "ucgen": 12, "hacim_cm3": 1.0, "alt_kenar_mm": 3.0,
     "parcalar": [], "girdi_sha256": "", "model_sha256": ""}
json.dump(o, open(os.path.join(c, "olcu.json"), "w"))
'''


def png_gri(w, h):
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ham = b"".join(b"\0" + bytes(((x * 255) // max(1, w - 1) + y) % 256 for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b""))


def _foto():
    return png_gri(64, 48)


# G2 hermetik vakalari: girdi (§2 zarfi) -> uretece giden BEKLENEN JSON (bagimsiz yazilmis; 9 renk de var).
G2_VAKA = {
    "isimlik": {"olcu": 120, "renkler": {"plaka": "Beyaz", "yazi": "Lacivert"},
                "parametreler": {"satirlar": "Ada\nKat 2", "kisa_kenar_mm": 50, "yazi_tipi": "Tırnaklı",
                                 "plaka_sekli": "Yuvarlak köşe", "montaj_delikleri": "Var"},
                "beklenen": {"satirlar": ["Ada", "Kat 2"], "genislik_mm": 120.0, "yukseklik_mm": 50.0,
                             "yazi_tipi": "serif-kalin", "plaka_sekli": "yuvarlak-kose", "montaj_delikleri": True,
                             "renk_plaka": "#F2F2F2", "renk_yazi": "#12294D"},
                "renk_sayisi": 2, "parcalar": ["plaka", "yazi"]},
    "qr": {"olcu": 90, "renkler": {"plaka": "Sarı", "kod": "Siyah"},
           "parametreler": {"metin": "https://pruvo3d.com/foto", "alt_yazi": "MENÜ", "cerceve": "Var"},
           "beklenen": {"metin": "https://pruvo3d.com/foto", "plaket_mm": 90.0, "alt_yazi": "MENÜ", "cerceve": True,
                        "renk_plaka": "#E8B923", "renk_qr": "#1A1A1A"},
           "renk_sayisi": 2, "parcalar": ["plaka", "kod"]},
    "logo": {"olcu": 80, "renkler": {"taban": "Gri", "logo": "Kırmızı"}, "parametreler": {"taban": "Var"},
             "dosyalar": {"svg": ("svg.svg", SVG_ORNEK.encode())},
             "beklenen": {"svg": SVG_ORNEK, "uzun_kenar_mm": 80.0, "taban": True, "renk_taban": "#818184",
                          "renk_logo": "#B3262E"},
             "renk_sayisi": 2, "parcalar": ["taban", "logo"]},
    "muhur": {"olcu": 40, "renkler": {"govde": "Yeşil", "sap": "Beyaz"}, "parametreler": {"sap": "Topuz"},
              "dosyalar": {"foto": ("foto.png", _foto)},
              "beklenen": {"gorsel": "foto.png", "yuz_mm": 40.0, "sap_renk": "ayri", "sap": "topuz",
                           "renk_govde": "#2E7D4F", "renk_sap": "#F2F2F2"},
              "renk_sayisi": 2, "parcalar": ["govde", "sap"]},
    "sablon": {"olcu": 100, "renkler": {"sablon": "Mavi"}, "parametreler": {"mod": "Dolu silüet"},
               "dosyalar": {"foto": ("foto.png", _foto)},
               "beklenen": {"gorsel": "foto.png", "uzun_kenar_mm": 100.0, "mod": "negatif", "renk": "#2E5E8C"},
               "renk_sayisi": 1, "parcalar": ["sablon"]},
    "yapboz": {"olcu": 150, "renkler": {"yapboz": "Ahşap"}, "parametreler": {"parca": "20"},
               "dosyalar": {"foto": ("foto.png", _foto)},
               "beklenen": {"gorsel": "foto.png", "uzun_kenar_mm": 150.0, "satir": 4, "sutun": 5,
                            "renkler": ["#C8B89A"]},
               "renk_sayisi": 1, "parcalar": ["yapboz"]},
    # G4 (kopru-15 DILIM-2) — YALNIZ gelen parametreler uretece gider (varsayilan enjeksiyonu YOK: eksik alan
    # uretecin kendi varsayilani; koşulu saglanmayan alan sunucuda zaten RED). renk_bolgeleri bos.
    "kutu": {"olcu": 100, "renkler": {}, "parametreler": {"en_mm": 100, "duvar_mm": 1.6, "kapak": True},
             "beklenen": {"en_mm": 100, "duvar_mm": 1.6, "kapak": True},
             "renk_sayisi": 1, "parcalar": []},
    "adaptor": {"olcu": 60, "renkler": {}, "parametreler": {"mod": "burc", "dis_cap_mm": 60, "flans": False},
                "beklenen": {"mod": "burc", "dis_cap_mm": 60, "flans": False},
                "renk_sayisi": 1, "parcalar": []},
    "disli": {"olcu": 60, "renkler": {}, "parametreler": {"dis_cap_mm": 60},
              "beklenen": {"dis_cap_mm": 60},
              "renk_sayisi": 1, "parcalar": []},
    "kapak": {"olcu": 60, "renkler": {}, "parametreler": {"mod": "kapak", "dis_cap_mm": 60},
              "beklenen": {"mod": "kapak", "dis_cap_mm": 60},
              "renk_sayisi": 1, "parcalar": []},
    # G4b (kopru-15) — dugme / klips / saksi: cap_mm (dugme+saksi) ve boru_cap_mm (klips boru_kelepcesi) olcu alanlari.
    "dugme": {"olcu": 30, "renkler": {}, "parametreler": {"cap_mm": 30, "mil_tipi": "d_mil", "mil_capi_mm": 6},
              "beklenen": {"cap_mm": 30, "mil_tipi": "d_mil", "mil_capi_mm": 6},
              "renk_sayisi": 1, "parcalar": []},
    "klips": {"olcu": 25, "renkler": {}, "parametreler": {"alt_tur": "boru_kelepcesi", "boru_cap_mm": 25, "vida": "M4"},
              "beklenen": {"alt_tur": "boru_kelepcesi", "boru_cap_mm": 25, "vida": "M4"},
              "renk_sayisi": 1, "parcalar": []},
    "saksi": {"olcu": 100, "renkler": {}, "parametreler": {"tur": "saksi", "cap_mm": 100, "profil": "silindir"},
              "beklenen": {"tur": "saksi", "cap_mm": 100, "profil": "silindir"},
              "renk_sayisi": 1, "parcalar": []},
    # G5 (kopru-15 DILIM-2) — gelen parametreler + bolge renkleri `renk_<bolge>`; bolge adlari MANIFESTTEN
    # (koordinat: plaka/yazi — kaydin renk_plaka/renk_yazi parametreleri), eski taban/yazi DEGIL.
    "koordinat": {"olcu": 160, "renkler": {"plaka": "Beyaz", "yazi": "Lacivert"},
                  "parametreler": {"enlem": 41.0082, "boylam": 28.9784, "genislik_mm": 160},
                  "beklenen": {"enlem": 41.0082, "boylam": 28.9784, "genislik_mm": 160,
                               "renk_plaka": "#F2F2F2", "renk_yazi": "#12294D"},
                  "renk_sayisi": 2, "parcalar": ["plaka", "yazi"]},
}


class Ortam:
    def __init__(self, kosucu=KOSUCU, tablo=True):
        self.d = tempfile.mkdtemp(prefix="foto-kosucu-test-")
        self.kosucu = kosucu
        self.db = os.path.join(self.d, "d1.sqlite")
        self.r2 = os.path.join(self.d, "r2")
        self.log = os.path.join(self.d, "wrangler.log")
        os.makedirs(self.r2)
        open(self.log, "w").close()
        self.tekin_log = os.path.join(self.d, "tekin.log")
        open(self.tekin_log, "w").close()
        for ad, icerik in (("wr.py", SAHTE_WRANGLER), ("uretec.py", SAHTE_URETEC), ("tekin.py", SAHTE_TEKIN)):
            with open(os.path.join(self.d, ad), "w") as f:
                f.write(icerik)
        c = sqlite3.connect(self.db)
        with open(SEMA, encoding="utf-8") as f:
            c.executescript(f.read())
        c.commit()
        c.close()
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log, FAKE_TEKIN_LOG=self.tekin_log,
                        FOTO_KOSUCU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")),
                        FOTO_KOSUCU_KILIT=os.path.join(self.d, "kilit"),
                        FOTO_KOSUCU_PYTHON=sys.executable)
        # Her D/R ciktisi onarim kapisindan gecer (8 Eki) -> varsayilan sahte kopru (FAKE_KOPRU=ok).
        self.env["FOTO_KOSUCU_JENERATOR"] = self.jen()
        for k in ("FAKE_D1_KAPALI", "FAKE_R2_KAPALI", "FAKE_CAS_KAYBI", "FAKE_URETEC_MOD", "FOTO_KOSUCU_URETEC_TABLO",
                  "FAKE_TEKIN_RET", "FAKE_TEKIN_EXTRUDER", "FAKE_KOPRU"):
            self.env.pop(k, None)
        if tablo:
            t = os.path.join(self.d, "tablo.json")
            with open(t, "w") as f:
                tablo_ek = {"litofan_uret": {"bicim": "sozlesme",
                                             "komut": [sys.executable, os.path.join(self.d, "uretec.py")]}}
                for u, esle in TEKIN_ESLE.items():
                    tablo_ek[u] = {"bicim": "tekin-ortak", "betik": os.path.join(self.d, "tekin.py"), "esle": esle}
                json.dump(tablo_ek, f)
            self.env["FOTO_KOSUCU_URETEC_TABLO"] = t

    def sql(self, q, *p):
        c = sqlite3.connect(self.db)
        c.row_factory = sqlite3.Row
        r = [dict(x) for x in c.execute(q, p).fetchall()]
        c.commit()
        c.close()
        return r

    def siparis_is(self, olcu=150, deneme=0):
        kalem = {"foto_is": IS, "foto_tur": "litofan", "olcu_mm": olcu,
                 "foto_secim": {"panel_renk": "Beyaz", "ayak_renk": "Siyah", "panel_malzeme": "PLA",
                                "ayak_malzeme": "PETG"}}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", olcu * 1000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS, "litofan", olcu, "uretec-bekliyor", deneme, GUNCEL0, GUNCEL0)
        os.makedirs(os.path.join(self.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(self.r2, "foto-onizleme", IS + ".png"), "wb") as f:
            f.write(png_gri(240, 160))

    def onizleme_is(self):
        self.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
                 " VALUES (?,?,?,?,?,?,?)", IS2, "litofan", 120, "ab" * 8, GUNCEL0, "uretec-onizleme", 5)
        d = os.path.join(self.r2, "foto-uretec-onizleme", IS2)
        os.makedirs(d)
        with open(os.path.join(d, "girdi.json"), "w") as f:
            json.dump({"sozlesme": 1, "kategori": "litofan", "siparis_no": "", "kalem": 0, "olcu_mm": 120,
                       "renkler": {}, "malzemeler": {}, "parametreler": {}, "dosyalar": {"gri_harita": "gri_harita.png"}}, f)
        with open(os.path.join(d, "gri_harita.png"), "wb") as f:
            f.write(png_gri(200, 140))

    def siparis_onizlemeden(self, secim):
        """Siparis oncesi uretec onizlemesine (IS2) bagli odenmis kalem."""
        kalem = {"foto_is": IS2, "foto_tur": "litofan", "olcu_mm": 120, "foto_secim": secim}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", 120000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS2, "litofan", 120, "uretec-bekliyor", 0, GUNCEL0, GUNCEL0)

    def uretec_onizleme(self, tur, olcu, renkler, parametreler, dosyalar=None, is_no=IS2):
        """Siparis oncesi uretec onizlemesi (foto_isler 'uretec-onizleme') + R2 girdi dizini."""
        self.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
                 " VALUES (?,?,?,?,?,?,?)", is_no, tur, olcu, "ab" * 8, GUNCEL0, "uretec-onizleme", 5)
        d = os.path.join(self.r2, "foto-uretec-onizleme", is_no)
        os.makedirs(d)
        beyan = {}
        for anahtar, (ad, bayt) in (dosyalar or {}).items():
            beyan[anahtar] = ad
            with open(os.path.join(d, ad), "wb") as f:
                f.write(bayt)
        with open(os.path.join(d, "girdi.json"), "w", encoding="utf-8") as f:
            json.dump({"sozlesme": 1, "kategori": tur, "siparis_no": "", "kalem": 0, "olcu_mm": olcu,
                       "renkler": renkler, "malzemeler": {}, "parametreler": parametreler, "dosyalar": beyan},
                      f, ensure_ascii=False)
        return d

    def tekin_girdileri(self):
        with open(self.tekin_log, encoding="utf-8") as f:
            return [json.loads(s) for s in f if s.strip()]

    def uretec_sayisi(self):
        with open(self.log) as f:
            return sum(1 for s in f if json.loads(s) == ["uretec"])

    def kos(self, *arg, **ek):
        env = dict(self.env, **ek)
        p = subprocess.run([sys.executable, self.kosucu] + list(arg), capture_output=True, text=True, env=env,
                           timeout=600)
        son = (p.stdout.strip().splitlines() or [""])[-1]
        return p.returncode, son, p.stdout + p.stderr

    def yazimlar(self):
        n = 0
        with open(self.log) as f:
            for s in f:
                a = json.loads(s)
                if a[:3] == ["r2", "object", "put"]:
                    n += 1
                elif a[:2] == ["d1", "execute"] and not a[a.index("--command") + 1].startswith("SELECT"):
                    n += 1
        return n

    def r2_put(self):
        with open(self.log) as f:
            return sum(1 for s in f if json.loads(s)[:3] == ["r2", "object", "put"])

    def uretim(self):
        r = self.sql("SELECT asama, sebep, deneme, guncel FROM foto_uretim")
        return r[0] if r else None

    def onarim_is(self, ham=True):
        """Saglayici zinciri bitti: foto_uretim 'onarim-bekliyor' + R2 model.ham.3mf (8 Eki onarim kuyrugu)."""
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS, "figur", 130, "onarim-bekliyor", 0, GUNCEL0, GUNCEL0)
        if ham:
            os.makedirs(os.path.join(self.r2, "foto", SIP, "0"), exist_ok=True)
            with open(os.path.join(self.r2, "foto", SIP, "0", "model.ham.3mf"), "wb") as f:
                f.write(HAM_3MF)

    def jen(self, kopru=True):
        """Sahte uretec deposu; kopru=False -> uc_mf_onar.py YOK."""
        d = os.path.join(self.d, "jen" if kopru else "jen-bos")
        os.makedirs(os.path.join(d, "jeneratorler", "foto"), exist_ok=True)
        if kopru:
            with open(os.path.join(d, "jeneratorler", "foto", "uc_mf_onar.py"), "w") as f:
                f.write(SAHTE_KOPRU)
        return d

    def model(self):
        y = os.path.join(self.r2, "foto", SIP, "0", "model.3mf")
        return open(y, "rb").read() if os.path.isfile(y) else None

    def kapat(self):
        shutil.rmtree(self.d, ignore_errors=True)


def vakalar(kosucu):
    """Donus {vaka: (gecti, aciklama)}."""
    s = {}

    def vaka(ad, fn):
        o = Ortam(kosucu)
        try:
            gecti, ac = fn(o)
        except Exception as e:  # vaka cokerse KIRMIZI
            gecti, ac = False, "istisna %s: %s" % (type(e).__name__, e)
        finally:
            o.kapat()
        s[ad] = (gecti, ac)

    def t1(o):
        rc, son, _ = o.kos("--uygula")
        return rc == 1 and son == "HAL=BOS rc=1" and o.yazimlar() == 0, son

    def t2(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        dosyalar = sorted(os.listdir(os.path.join(o.r2, "foto", SIP, "0"))) if os.path.isdir(
            os.path.join(o.r2, "foto", SIP, "0")) else []
        return (rc == 0 and son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir"
                and dosyalar == ["model.3mf", "olcu.json", "onizleme.png"]), "%s %s %s" % (son, u, dosyalar)

    def t3(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="red")
        u = o.uretim()
        return (rc == 0 and son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and u["asama"] == "elle"
                and u["sebep"] == "uretec-red:olcu-aralik" and o.r2_put() == 0), "%s %s" % (son, u)

    def t4(o):
        o.siparis_is()
        izler = []
        for _ in range(3):
            rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="ariza")
            u = o.uretim()
            izler.append((son, u["asama"], u["deneme"]))
        ok = (izler[0][1:] == ("uretec-bekliyor", 1) and izler[1][1:] == ("uretec-bekliyor", 2) and
              izler[2][1] == "elle" and o.uretim()["sebep"] == "uretec-ariza" and
              izler[2][0] == "HAL=ISLEDI uretildi=0 red=0 ariza=1 rc=0" and o.r2_put() == 0)
        return ok, str(izler)

    def t5(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="sizdirmaz")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "sizdirmaz-degil" and o.r2_put() == 0
                and son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0"), "%s %s put=%d" % (son, u, o.r2_put())

    def t6(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_CAS_KAYBI="1")
        u = o.uretim()
        return (u["asama"] == "hazir" and u["guncel"] == "baska-kosucu" and o.r2_put() == 0 and
                not os.path.isdir(os.path.join(o.r2, "foto"))), "%s %s put=%d" % (son, u, o.r2_put())

    def t7(o):
        o.siparis_is()
        once = o.uretim()
        rc1, son1, _ = o.kos("--uygula", FAKE_D1_KAPALI="1")
        ara = o.uretim()
        # R2 kapali: kiralama olur, gri harita indirilemez -> jeton geri verilir, satir ayni
        rc2, son2, _ = o.kos("--uygula", FAKE_R2_KAPALI="1")
        sonra = o.uretim()
        return (rc1 == 4 and son1 == "HAL=OLCULEMEDI sebep=d1 rc=4" and ara == once and
                rc2 == 4 and son2 == "HAL=OLCULEMEDI sebep=r2 rc=4" and sonra == once and o.r2_put() == 0), \
            "%s | %s | %s -> %s" % (son1, son2, once, sonra)

    def t8(o):
        o.siparis_is()
        fd = os.open(o.env["FOTO_KOSUCU_KILIT"], os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            rc, son, _ = o.kos("--uygula")
        finally:
            os.close(fd)
        rc2, son2, _ = o.kos("--uygula")  # kilit birakildi (sahibi oldu) -> devralinir
        return (rc == 3 and son == "HAL=KILITLI rc=3" and rc2 == 0 and son2.startswith("HAL=ISLEDI uretildi=1")), \
            "%s | %s" % (son, son2)

    def t9(o):
        o.siparis_is()
        once = o.uretim()
        rc, son, cikti = o.kos()
        return (rc == 0 and son == "HAL=PLAN is=1 rc=0" and o.yazimlar() == 0 and o.uretim() == once and
                "PLAN R2 PUT pruvo-ozel/foto/%s/0/model.3mf" % SIP in cikti), "%s yazim=%d" % (son, o.yazimlar())

    def t10(o):
        o.onizleme_is()
        rc, son, _ = o.kos("--uygula")
        r = o.sql("SELECT asama, hata, hazir_tarih FROM foto_isler WHERE is_no = ?", IS2)[0]
        d = os.path.join(o.r2, "foto-uretec-onizleme", IS2)
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and r["asama"] == "onizleme-hazir" and
                r["hazir_tarih"] != "" and sorted(os.listdir(d)) ==
                ["girdi.json", "gri_harita.png", "model.3mf", "olcu.json", "onizleme.png"]), "%s %s" % (son, r)

    def t12(o):
        # KOPYA KOLU: onizleme -> onizleme-hazir (uretec 1) -> ayni girdili siparis -> uretec KOSMAZ.
        o.onizleme_is()
        o.kos("--uygula")
        o.siparis_onizlemeden({})
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        m0 = os.path.join(o.r2, "foto-uretec-onizleme", IS2, "model.3mf")
        ayni = (sorted(os.listdir(d)) == ["model.3mf", "olcu.json", "onizleme.png"] if os.path.isdir(d) else False) and \
            open(os.path.join(d, "model.3mf"), "rb").read() == open(m0, "rb").read()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.uretec_sayisi() == 1 and "KOPYA" in cikti and ayni), "%s %s uretec=%d ayni=%s" % (
                    son, u, o.uretec_sayisi(), ayni)

    def t12b(o):
        # SHA FARKLI: siparis secimi onizleme girdisinden farkli -> kopya YOK, uretec yeniden koşar.
        o.onizleme_is()
        o.kos("--uygula")
        o.siparis_onizlemeden({"ayak_renk": "Siyah"})
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.uretec_sayisi() == 2 and "KOPYA" not in cikti), "%s %s uretec=%d" % (son, u, o.uretec_sayisi())

    def t11(o):
        log = os.path.join(o.d, "k.log")
        with open(log, "w") as f:
            f.write("x" * 6 * 1024 * 1024)
        with open(log + ".1", "w") as f:
            f.write("eski")
        rc, son, _ = o.kos("--log", log)
        b1 = os.path.getsize(log)
        b2 = os.path.getsize(log + ".1")
        return (son == "HAL=BOS rc=1" and b1 < 1024 and b2 == 6 * 1024 * 1024 and
                not os.path.exists(log + ".2")), "log=%d log.1=%d" % (b1, b2)

    # ---- G2 tekin-ortak koprusu: her kategori icin uretece giden JSON BIREBIR beklenen.
    def t13(kod):
        def fn(o):
            x = G2_VAKA[kod]
            dosya = {k: (ad, b() if callable(b) else b) for k, (ad, b) in x.get("dosyalar", {}).items()}
            d = o.uretec_onizleme(kod, x["olcu"], x["renkler"], x["parametreler"], dosya)
            rc, son, cikti = o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            gelen = o.tekin_girdileri()
            g = dict(gelen[0]) if len(gelen) == 1 else {}
            if "gorsel" in g:
                g["gorsel"] = os.path.basename(g["gorsel"])
            olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
            b = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24]) \
                if os.path.isfile(os.path.join(d, "onizleme.png")) else (0, 0)
            ok = (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and r["asama"] == "onizleme-hazir" and
                  g == x["beklenen"] and olcu.get("renk_sayisi") == x["renk_sayisi"] and
                  olcu.get("uzun_kenar_mm") == float(x["olcu"]) and olcu.get("kategori") == kod and
                  re.match(r"^[0-9a-f]{64}$", olcu.get("girdi_sha256") or "") is not None and max(b) >= 1024 and
                  [p["ad"] for p in olcu.get("parcalar", [])] == x["parcalar"])
            fark = {k: (g.get(k), v) for k, v in x["beklenen"].items() if g.get(k) != v}
            fark.update({k: (g[k], None) for k in g if k not in x["beklenen"]})
            return ok, "%s %s fark=%s renk_sayisi=%s uk=%s" % (son, r, fark, olcu.get("renk_sayisi"),
                                                               olcu.get("uzun_kenar_mm"))
        return fn

    def t14(o):
        o.uretec_onizleme("isimlik", 120, {"plaka": "Beyaz", "yazi": "Gri"}, {"satirlar": "Ada", "kisa_kenar_mm": 40})
        rc, son, _ = o.kos("--uygula", FAKE_TEKIN_RET="plaka/yazi renk kontrasti 2.10 < 3.0 (acik/koyu cift sec)")
        r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
        return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and r["asama"] == "basarisiz" and
                r["hata"] == "uretec-red:kontrast"), "%s %s" % (son, r)

    def t_kosmaz(kod, olcu, renkler, parametreler, beklenen_hata):
        def fn(o):
            o.uretec_onizleme(kod, olcu, renkler, parametreler)
            rc, son, _ = o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and r["asama"] == "basarisiz" and
                    r["hata"] == beklenen_hata and o.tekin_girdileri() == []), "%s %s tekin=%d" % (
                        son, r, len(o.tekin_girdileri()))
        return fn

    def t17(o):
        x = G2_VAKA["isimlik"]
        d = o.uretec_onizleme("isimlik", x["olcu"], x["renkler"], x["parametreler"])
        rc, son, _ = o.kos("--uygula", FAKE_TEKIN_EXTRUDER="3")
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        return son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and olcu.get("renk_sayisi") == 3, \
            "%s renk_sayisi=%s" % (son, olcu.get("renk_sayisi"))

    # ---- G2b mimar kararlari (7 Eki): plaka 300 (manifest PLAKA_MM) · yapboz 100-190 · uzun kenar geometriden.
    def t19(o):
        x = G2_VAKA["logo"]
        sonuc = {}
        for kutu in (290, 310):
            no = ("%032x" % kutu)
            o.uretec_onizleme("logo", x["olcu"], x["renkler"], x["parametreler"],
                              {k: (ad, b() if callable(b) else b) for k, (ad, b) in x.get("dosyalar", {}).items()},
                              is_no=no)
            o.kos("--uygula", FAKE_TEKIN_KUTU=str(kutu))
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", no)[0]
            sonuc[kutu] = (r["asama"], r["hata"])
        return (sonuc[290][0] == "onizleme-hazir" and sonuc[310][0] != "onizleme-hazir" and
                "plaka-disi" in (sonuc[310][1] or "")), "%s" % sonuc

    def t20(o):
        x = G2_VAKA["logo"]
        # ozet NOMINAL uzun kenari 80 der, 3MF geometrisi 78,4 (%2) -> kosucu geometriyi olcer, tolerans RED.
        o.uretec_onizleme("logo", x["olcu"], x["renkler"], x["parametreler"],
                          {k: (ad, b() if callable(b) else b) for k, (ad, b) in x.get("dosyalar", {}).items()})
        o.kos("--uygula", FAKE_TEKIN_GEO="0.98")
        r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
        return (r["asama"] != "onizleme-hazir" and "uzun-kenar-tolerans" in (r["hata"] or "")), "%s" % (r,)

    def t21(o):
        sonuc = {}
        for olcu in (190, 200):
            no = ("%032x" % olcu)
            o.uretec_onizleme("yapboz", olcu, {"yapboz": "Ahşap"}, {"parca": "12"}, {"foto": ("foto.png", png_gri(64, 48))},
                              is_no=no)
            o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", no)[0]
            sonuc[olcu] = (r["asama"], r["hata"])
        return (sonuc[190][0] == "onizleme-hazir" and sonuc[200][0] != "onizleme-hazir" and
                "olcu-aralik-disi" in (sonuc[200][1] or "")), "%s" % sonuc

    for kod in G2_VAKA:
        vaka("T13-" + kod, t13(kod))
    vaka("T19", t19)
    vaka("T20", t20)
    vaka("T21", t21)
    vaka("T14", t14)
    vaka("T15", t_kosmaz("isimlik", 80, {"plaka": "Beyaz", "yazi": "Siyah"}, {"satirlar": "Ada", "kisa_kenar_mm": 90},
                         "uretec-red:kisa-kenar"))
    vaka("T16", t_kosmaz("qr", 80, {"plaka": "Pembe", "kod": "Siyah"}, {"metin": "https://pruvo3d.com"},
                         "uretec-red:renk"))
    vaka("T17", t17)
    vaka("T18", t_kosmaz("qr", 80, {"plaka": "Beyaz", "kod": "Siyah"}, {"metin": "https://pruvo3d.com", "renk": "x"},
                         "uretec-red:parametre"))
    # ---- ORNEK kolu + hedef (8 Eki 2026; tools/foto-ornek-uc-uca.py zinciri).
    ornek_no = "ORNEK-" + IS2[:12]

    def ornek_uretim(o, tur, olcu):
        o.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
              " VALUES (?,0,?,?,?,?,?,?,?)", ornek_no, IS2, tur, olcu, "uretec-bekliyor", 0, GUNCEL0, GUNCEL0)

    def t22(o):
        x = G2_VAKA["isimlik"]
        o.uretec_onizleme("isimlik", x["olcu"], x["renkler"], x["parametreler"])
        o.sql("UPDATE foto_isler SET ziyaretci = 'ornek' WHERE is_no = ?", IS2)
        o.kos("--uygula")
        ornek_uretim(o, "isimlik", x["olcu"])
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", ornek_no, "0")
        dosya = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                dosya == ["model.3mf", "olcu.json", "onizleme.png"] and "KOPYA" in cikti and
                len(o.tekin_girdileri()) == 1), "%s %s dosya=%s tekin=%d" % (son, u, dosya, len(o.tekin_girdileri()))

    def t23(o):
        # Musteri isi (ziyaretci ozeti) ORNEK numarasiyla URETILEMEZ.
        x = G2_VAKA["isimlik"]
        o.uretec_onizleme("isimlik", x["olcu"], x["renkler"], x["parametreler"])
        o.kos("--uygula")
        ornek_uretim(o, "isimlik", x["olcu"])
        put0 = o.r2_put()
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "ornek-gecersiz" and o.r2_put() == put0), "%s %s" % (son, u)

    def t24(o):
        o.kos("--hedef", "onizleme")
        o.kos()
        # Bos kuyrukta her kosum 3 SELECT (siparis + onizleme + onarim kuyrugu, 8 Eki).
        adlar = [a[2] for a in (json.loads(s) for s in open(o.log)) if a[:2] == ["d1", "execute"]]
        return (len(adlar) == 6 and set(adlar[:3]) == {"pruvo-katalog-onizleme"} and
                set(adlar[3:]) == {"pruvo-katalog"}), "%s" % adlar

    def t25(o):
        # Tarayici onizleyicili tur (litofan): ornek isi 'hazir' + gri harita -> ORNEK siparis uretilir.
        o.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
              " VALUES (?,?,?,?,?,?,?)", IS2, "litofan", 140, "ornek", GUNCEL0, "hazir", 0)
        os.makedirs(os.path.join(o.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(o.r2, "foto-onizleme", IS2 + ".png"), "wb") as f:
            f.write(png_gri(200, 140))
        ornek_uretim(o, "litofan", 140)
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        return son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir", "%s %s" % (son, u)

    def t26(o):
        # kopru-15 DILIM-3 TURETILMIS eksen (kutu): onizleme olcu 0 (surgu yok) -> koşucu 3MF'ten OLCULEN uzun
        # kenari (yarim yukari) satirin olcu_mm'sine yazar; aralik (40..300) disi -> uretec reddi, olcu yazilmaz.
        x = G2_VAKA["kutu"]
        o.uretec_onizleme("kutu", 0, x["renkler"], dict(x["parametreler"], en_mm=123))
        rc, son, cikti = o.kos("--uygula", FAKE_TEKIN_GEO="1.004")
        r = o.sql("SELECT asama, hata, olcu_mm FROM foto_isler WHERE is_no = ?", IS2)[0]
        ok1 = son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and r["asama"] == "onizleme-hazir" and r["olcu_mm"] == 123
        o.sql("DELETE FROM foto_isler WHERE is_no = ?", IS2)
        shutil.rmtree(os.path.join(o.r2, "foto-uretec-onizleme", IS2))
        o.uretec_onizleme("kutu", 0, x["renkler"], dict(x["parametreler"], en_mm=290))
        rc2, son2, _ = o.kos("--uygula", FAKE_TEKIN_GEO="1.1")
        r2 = o.sql("SELECT asama, hata, olcu_mm FROM foto_isler WHERE is_no = ?", IS2)[0]
        ok2 = r2["asama"] == "basarisiz" and r2["hata"] == "uretec-red:olcu-aralik-disi" and r2["olcu_mm"] == 0
        return ok1 and ok2, "olculen=%s %s | aralik_disi=%s %s" % (son, dict(r), son2, dict(r2))

    vaka("T22", t22)
    vaka("T23", t23)
    vaka("T26", t26)
    # ONARIM KUYRUGU (8 Eki 2026): 'onarim-bekliyor' -> kopru -> --olc -> model.3mf + 'hazir' ya da 'elle'.
    def t27(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.model() == HAM_3MF + b"ONARILDI"), "%s %s" % (son, u)

    def t28(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="olc-kirmizi")
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and u["asama"] == "elle" and
                u["sebep"] == "onarim-kirmizi" and o.model() is None), "%s %s" % (son, u)

    def t29(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(kopru=False))
        u = o.uretim()
        return (son == "HAL=OLCULEMEDI sebep=kopru-yok rc=4" and u["asama"] == "onarim-bekliyor" and
                u["guncel"] == GUNCEL0 and o.model() is None), "%s %s" % (son, u)

    def t30(o):
        o.onarim_is(ham=False)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-ham-yok" and o.model() is None), "%s %s" % (son, u)

    def t31(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="girdi")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-girdi-hatasi" and o.model() is None), "%s %s" % (son, u)

    # D/R CIKTISINA AYNI KAPI (8 Eki): tek dosya --olc kirmizi -> kopru -> gecerse onarilmis model + yeni sha.
    def t32(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_KOPRU="tek-kirmizi")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        model = open(os.path.join(d, "model.3mf"), "rb").read() if os.path.isfile(os.path.join(d, "model.3mf")) else b""
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                model.endswith(b"ONARILDI") and olcu.get("model_sha256") == hashlib.sha256(model).hexdigest() and
                sorted(os.listdir(d)) == ["model.3mf", "olcu.json", "onizleme.png"]), "%s %s" % (son, u)

    def t33(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_KOPRU="olc-kirmizi")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-kirmizi" and
                not os.path.isdir(os.path.join(o.r2, "foto", SIP))), "%s %s" % (son, u)

    def t34(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(kopru=False))
        u = o.uretim()
        return (son == "HAL=OLCULEMEDI sebep=kopru-yok rc=4" and u["asama"] == "uretec-bekliyor" and
                u["guncel"] == GUNCEL0), "%s %s" % (son, u)

    vaka("T24", t24)
    vaka("T25", t25)
    vaka("T32", t32)
    vaka("T33", t33)
    vaka("T34", t34)
    vaka("T27", t27)
    vaka("T28", t28)
    vaka("T29", t29)
    vaka("T30", t30)
    vaka("T31", t31)
    for ad, fn in (("T1", t1), ("T2", t2), ("T3", t3), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7),
                   ("T8", t8), ("T9", t9), ("T10", t10), ("T11", t11), ("T12", t12), ("T12b", t12b)):
        vaka(ad, fn)
    return s


MUTANTLAR = {
    "M1": ('    if o.get("sizdirmaz") is not True:\n        return "sizdirmaz-degil"\n', "", {"T5"}),
    "M2": ("        if not uygula:\n", "        if False:\n", {"T9"}),
    "M3": ('    if n != 1:\n        yaz("CAS %s kiralanamadi', '    if False:\n        yaz("CAS %s kiralanamadi', {"T6"}),
    "M4": ("DENEME_TAVANI = 3\n", "DENEME_TAVANI = 99\n", {"T4"}),
    "M5": ("            d1(geri_ver_sql(i, jeton))\n", "            pass\n", {"T7", "T34"}),
    "M6": ("    if onceki != sha:\n", "    if False:\n", {"T12b"}),
    "M7": ('    if i["kuyruk"] != "siparis" or not i.get("onizleme_kaynakli"):\n        return None\n    os.makedirs',
           '    if True:\n        return None\n    os.makedirs', {"T12", "T22"}),  # T22: ORNEK kolu da kopya koluna baglanir
    # G2 tekin-ortak koprusu
    "M8": ("    return renk_hex[ad]\n", "    return \"#F2F2F2\"\n", {"T13-" + k for k in G2_VAKA if k in ("isimlik", "qr", "logo", "muhur", "sablon", "yapboz", "koordinat")}),
    "M9": ('    u = {"metin": m, "plaket_mm": float(g["olcu_mm"])}\n',
           '    u = {"metin": m, "uzun_kenar_mm": float(g["olcu_mm"])}\n', {"T13-qr"}),
    "M10": ('"yuz_mm": float(g["olcu_mm"])', '"uzun_kenar_mm": float(g["olcu_mm"])', {"T13-muhur"}),
    "M11": ('    (r"kontrast", "kontrast"),\n', "", {"T14"}),
    "M12": ('"renk_sayisi": uc_mf_extruder_sayisi(os.path.join(cikti, "model.3mf")),',
            '"renk_sayisi": len(bolgeler),',
            {"T17", "T13-kutu", "T13-adaptor", "T13-disli", "T13-kapak", "T26",
             "T13-dugme", "T13-klips", "T13-saksi"}),
    "M13": ('        if any(k not in form for k in (girdi.get("parametreler") or {})):\n            raise KopruRed("parametre")\n',
            "", {"T18"}),
    # G2b: plaka 300 tek kaynak · uzun kenar geometriden · yapboz araligi
    "M14": ("0 < k[e] <= plaka_mm() for e in", "0 < k[e] <= 250 for e in", {"T19"}),
    "M15": ("0 < k[e] <= plaka_mm() for e in", "0 < k[e] <= 9999 for e in", {"T19"}),
    "M16": ('    uk = uc_mf_uzun_kenar(os.path.join(cikti, "model.3mf"), oz)\n',
            '    uk = oz.get("uzun_kenar_mm") or max(kutu[0], kutu[1])\n', {"T20", "T26"}),
    "M17": ('<= i["olcu_mm"] <= a.get("en_cok", 0)):\n        return "olcu-aralik-disi"',
            '<= i["olcu_mm"] <= 99999):\n        return "olcu-aralik-disi"', {"T21"}),
    "M18": ('    if i.get("is_ziyaretci") != ORNEK_ZIYARETCI or ', "    if ", {"T23"}),
    "M19": ('    D1_AD, R2_KOVA, HEDEF = db.group(1), kova.group(1), "onizleme"', '    HEDEF = "onizleme"', {"T24"}),
    # G4 (kopru-15) — esle_<kod> ESLEMELER'den silinince uretec-bicimi RED'lenir (TEKIN_ESLE'de uretec adina
    # baglanan esleme kapisi kalkar); sadece o turun T13 vakasi KIRMIZI olur.
    "M20": ('             "kutu": esle_kutu,\n', "", {"T13-kutu", "T26"}),  # T26 = kutu turetilmis olcusu
    "M21": ('             "adaptor": esle_adaptor,\n', "", {"T13-adaptor"}),
    "M22": ('             "disli": esle_disli,\n', "", {"T13-disli"}),
    "M23": ('             "kapak": esle_kapak,\n', "", {"T13-kapak"}),
    # kopru-15 DILIM-2: G4 esle varsayilan enjekte ederse (eski davranis) G4 T13'leri KIRMIZI; G5 bolge adi
    # manifestten degil sabit `taban`dan okunursa koordinat renkleri dusur -> T13-koordinat KIRMIZI.
    "M24": ('    return dict(g.get("parametreler") or {}), []\n',
            '    return dict({"yukseklik_mm": 40}, **(g.get("parametreler") or {})), []\n',
            {"T13-kutu", "T13-adaptor", "T13-disli", "T13-kapak",
             "T13-dugme", "T13-klips", "T13-saksi"}),
    "M25": ('            u["renk_" + b] = h\n', '            u["renk_taban"] = h\n', {"T13-koordinat"}),
    # kopru-15 DILIM-3: tolerans dali TURETILMIS turde hedefe (olcu 0) donerse / olculen olcu satira
    # yazilmazsa / aralik kontrolu kalkarsa T26 KIRMIZI.
    "M26": ('(not tu and abs(uk - i["olcu_mm"])', '(abs(uk - i["olcu_mm"])', {"T26"}),
    "M27": ('                st += ", olcu_mm = %d" % int(olcu)\n', '                pass\n', {"T26"}),
    "M28": ('a.get("en_az", 1) <= olculen_mm(uk) <= a.get("en_cok", 0)):', 'True):', {"T26"}),
    # G4b (kopru-15) — dugme/klips/saksi ESLEMELER'den silinince uretec-bicimi RED.
    "M29": ('             "dugme": esle_dugme,\n', "", {"T13-dugme"}),
    "M30": ('             "klips": esle_klips,\n', "", {"T13-klips"}),
    "M31": ('             "saksi": esle_saksi,\n', "", {"T13-saksi"}),
    # ONARIM KUYRUGU (8 Eki): olcum atlanirsa kirmizi kopru ciktisi 'hazir' olur.
    "M32": ('        rc, hata, cik = kos(["--olc", ham, cikti])\n', '        rc, hata, cik = 0, "", "{}"\n', {"T28", "T33"}),
    # kopru-yok fail-closed silinirse is kuyrukta kalmaz (python dosya bulamaz -> elle).
    "M33": ('        raise Erisilemedi("kopru-yok")\n', "        pass\n", {"T29", "T34"}),
    # erisim yokken kira geri verilmezse satirin jetonu kayar.
    "M34": ("            d1(geri_ver_sql(i, jeton))  # onarim kuyrugu: kira geri (kopru/R2/D1 yok -> is kuyrukta)\n",
            "            pass\n", {"T29"}),
    # ham dosya yoksa kopru yine kosarsa sebep yanlis kovaya duser.
    "M35": ('            karar, sebep, ozet = "elle", "onarim-ham-yok", ""\n',
            "            karar, sebep, ozet = onarim_kapisi(ham, cikti)\n", {"T30"}),
    # D/R ciktisina kapi baglanmazsa kirmizi model teslim edilir (T33) ve kopru yokken is ilerler (T34).
    "M36": ("            sebep = cikti_dogrula(i, t, cikti) or d_kapisi(cikti)\n",
            "            sebep = cikti_dogrula(i, t, cikti)\n", {"T32", "T33", "T34"}),
    # onarilmis modelde olcu.json sha tazelenmezse ④ alanlar=0 olur.
    "M37": ('        olcu["model_sha256"] = hashlib.sha256(f.read()).hexdigest()\n', "        pass\n", {"T32"}),
    "M0": ("import argparse\n", "import argparse  # kontrol mutanti\n", set()),
}


def mutant_kos(ad):
    eski, yeni, hedef = MUTANTLAR[ad]
    with open(KOSUCU, encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        return False, "capa %d kez bulundu" % kaynak.count(eski)
    d = tempfile.mkdtemp(prefix="foto-kosucu-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "shop"))
        shutil.copyfile(os.path.join(KOK, "foto-uretim-veri.js"), os.path.join(d, "foto-uretim-veri.js"))
        shutil.copyfile(os.path.join(KOK, "shop", "wrangler.onizleme.toml"), os.path.join(d, "shop", "wrangler.onizleme.toml"))
        yol = os.path.join(d, "tools", "foto-uretec-kosucu.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni))
        s = vakalar(yol)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    kirmizi = {k for k, (g, _) in s.items() if not g}
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


def uctan_uca():
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    o = Ortam(tablo=False)
    try:
        o.env["FOTO_KOSUCU_JENERATOR"] = jen
        o.siparis_is(olcu=150)
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        z = zipfile.ZipFile(os.path.join(d, "model.3mf"))
        xml = z.read([n for n in z.namelist() if n.endswith(".model")][0]).decode()
        birim = re.search(r'unit="([a-z]+)"', xml).group(1)
        nesneler = re.findall(r"<object\b.*?</object>", xml, re.S)
        kutular = []
        for n in nesneler:
            xs = [float(v) for v in re.findall(r'<vertex x="([-0-9.e]+)"', n)]
            ys = [float(v) for v in re.findall(r'<vertex x="[-0-9.e]+" y="([-0-9.e]+)"', n)]
            kutular.append((round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3)))
        panel_uzun = max(kutular[0]) if kutular else 0
        w, h = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24])
        print("UCTAN_UCA son=%s" % son)
        print("asama=%s sebep=%r deneme=%s" % (u["asama"], u["sebep"], u["deneme"]))
        print("r2=%s" % sorted(os.listdir(d)))
        print("olcu.json sizdirmaz=%s uzun_kenar_mm=%s kutu=%s renk=%s ucgen=%s" % (
            olcu.get("sizdirmaz"), olcu.get("uzun_kenar_mm"), olcu.get("kutu_mm"), olcu.get("renk_sayisi"),
            olcu.get("ucgen")))
        print("3mf unit=%s nesne=%d panel_kutu_xy=%s bagimsiz_uzun_kenar=%s sapma=%.4f%%" % (
            birim, len(nesneler), kutular[0] if kutular else None, panel_uzun, abs(panel_uzun - 150) / 1.5))
        print("onizleme.png %dx%d" % (w, h))
        ok = (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
              olcu.get("sizdirmaz") is True and abs(panel_uzun - 150) <= 1.5 and birim == "millimeter")
        print("UCTAN_UCA_HUKUM=%s" % ("GECTI" if ok else "KIRMIZI"))
        if not ok:
            print(cikti)
        return 0 if ok else 1
    finally:
        o.kapat()


# ------------------------------------------------------------------ manifest tutarliligi (G2)
def kosucu_modulu():
    import importlib.util
    sp = importlib.util.spec_from_file_location("foto_uretec_kosucu", KOSUCU)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


# Mimar karari 7 Eki 2026 — AYNEN (manifest bunlarla birebir esit olmali).
G2_SATIR = {
    "isimlik": ("İsimlik / kapı tabelası", ["form"], "isimlik_uret", 10, 250, ["plaka", "yazi"], ["PLA", "PETG", "ASA"],
                "Üretim dosyasının görüntüsüdür; isimlik bu yazı ve ölçüyle üretilir, renk tonu filamente göre biraz değişebilir.",
                "Yazı plakanın üzerinde kabartmadır. Uzun metin küçülür; en küçük harf 6 mm'dir, sığmayan metin için sipariş alınmaz."),
    "qr": ("QR kodlu plaka", ["form"], "qr_plaket_uret", 10, 150, ["plaka", "kod"], ["PLA", "PETG", "ASA"],
           "Üretim dosyasının görüntüsüdür; plakadaki kod bu düzende üretilir.",
           "Kodu göndermeden önce telefonla okutarak kontrol ederiz. Bağlantının çalışması verdiğin adrese bağlıdır."),
    "logo": ("Logodan kabartma", ["svg"], "svg_ekstruzyon_uret", 10, 200, ["taban", "logo"], ["PLA", "PETG"],
             "Üretim dosyasının görüntüsüdür; logonun dolu alanları kabartma olarak üretilir.",
             "Yalnız düz renkli alanlar üretilir; gölge ve renk geçişi çıkmaz. 0,8 mm'den ince çizgiler siparişi durdurur."),
    "muhur": ("Logo mühür / damga", ["foto-1"], "muhur_uret", 10, 100, ["govde", "sap"], ["PLA", "PETG"],
              "Üretim dosyasının görüntüsüdür; damga yüzü ayna görüntüsüdür, kâğıda bastığında logonun kendisi çıkar.",
              "Plastik gövdeli bir damgadır; resmî kurum mührü yerine geçmez. 0,6 mm'den ince çizgiler kalınlaştırılır."),
    "sablon": ("Silüet şablon", ["foto-1"], "siluet_sablon_uret", 10, 250, ["sablon"], ["PLA", "PETG"],
               "Üretim dosyasının görüntüsüdür; açık alanlar delik, koyu alanlar plakadır.",
               "Şablon 1,2–2 mm kalınlığında bir plakadır; içteki adalar ince köprülerle tutturulur ve bu köprüler boyamada iz bırakır."),
    "yapboz": ("Fotoğraftan kabartma yapboz", ["foto-1"], "yapboz_uret", 10, 190, ["yapboz"], ["PLA", "PETG"],
               "Üretim dosyasının görüntüsüdür; fotoğrafın açık-koyu tonları kabartma yüksekliğine çevrilir.",
               "Yapboz tek renkli kabartmadır; renkli baskı değildir. Parçalar elle takılır; çocuk oyuncağı olarak belgelendirilmemiştir."),
}
RENK_HEX_KARAR = {"Beyaz": "#F2F2F2", "Siyah": "#1A1A1A", "Gri": "#818184", "Lacivert": "#12294D",
                  "Kırmızı": "#B3262E", "Sarı": "#E8B923", "Yeşil": "#2E7D4F", "Mavi": "#2E5E8C", "Ahşap": "#C8B89A"}
# Uretec girdi semalarinin alan adlari (G1-SEMA/G2-SEMA); `--gercek` kolu GERCEK uretecle dogrular.
URETEC_ALANLARI = {
    "isimlik": {"satirlar", "yazi_tipi", "hizalama", "plaka_sekli", "genislik_mm", "yukseklik_mm", "kose_yaricap_mm",
                "yazi_yuksekligi_mm", "kenar_payi_mm", "montaj_delikleri", "delik_cap_mm", "renk_plaka", "renk_yazi"},
    "qr": {"metin", "hata_duzeltme", "plaket_mm", "plaka_sekli", "kose_yaricap_mm", "cerceve", "alt_yazi", "yazi_tipi",
           "renk_plaka", "renk_qr"},
    "logo": {"svg", "uzun_kenar_mm", "kalinlik_mm", "taban", "taban_kalinlik_mm", "taban_pay_mm", "taban_sekli",
             "kose_yaricap_mm", "cizgi_dolgu", "min_cizgi_mm", "renk_taban", "renk_logo"},
    "muhur": {"gorsel", "yuz_mm", "kenar_mm", "esik", "ince_cizgi", "sap", "sap_yukseklik_mm", "sap_renk", "renk_govde",
              "renk_sap"},
    "sablon": {"gorsel", "uzun_kenar_mm", "kalinlik_mm", "mod", "esik", "kopru_mm", "renk"},
    "yapboz": {"gorsel", "uzun_kenar_mm", "satir", "sutun", "tohum", "kabartma_yon", "renkler"},
}
URETEC_OLCU_ALANI = {"isimlik": "genislik_mm", "qr": "plaket_mm", "logo": "uzun_kenar_mm", "muhur": "yuz_mm",
                     "sablon": "uzun_kenar_mm", "yapboz": "uzun_kenar_mm"}

NODE_MANIFEST = r"""
const vm=require('vm'),fs=require('fs');const k={};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});
const F=k.PRUVO_FOTO, o={};
o.turler=F.turler; o.renk_hex=F.RENK_HEX; o.red=F.URETEC_RED_METIN; o.tarayici=F.TARAYICI_ONIZLEYICI;
o.onay_surum=F.onay_surum; o.ornek_turler=F.ornekler.map(x=>x.tur); o.plaka=F.PLAKA_MM;
o.ornek_render=F.ornekler.filter(x=>x.kanit==='render').map(x=>[x.tur,x.render,x.onizleme]);
o.onay_anahtar=Object.keys(F.onay).sort(); o.hak_fn=typeof F.hakGerekir+'/'+typeof F.aktarimGerekir;
o.kol={}; for (const t of F.turler) o.kol[t.kod]=F.kolu(t.kod);
o.red_kontrast=F.uretecRedMetni('uretec-red:kontrast'); o.red_bilinmez=F.uretecRedMetni('uretec-red:yok-boyle');
o.red_genel=F.uretecRedMetni('uretec-red');
const P=(kod,p)=>F.parametreDogrula(kod,p);
const isim={satirlar:'Ada\nKat 2',kisa_kenar_mm:40,yazi_tipi:'Düz',plaka_sekli:'Oval',montaj_delikleri:'Yok'};
o.p={
  isim_ok:P('isimlik',isim).ok,
  isim_4satir:P('isimlik',Object.assign({},isim,{satirlar:'a\nb\nc\nd'})).ok,
  isim_41:P('isimlik',Object.assign({},isim,{satirlar:'x'.repeat(41)})).ok,
  isim_bos_satir:P('isimlik',Object.assign({},isim,{satirlar:'Ada\n\nKat'})).ok,
  isim_secim:P('isimlik',Object.assign({},isim,{yazi_tipi:'Kalın'})).ok,
  qr_altsiz:P('qr',{metin:'https://pruvo3d.com',cerceve:'Yok'}),
  qr_alt:P('qr',{metin:'https://pruvo3d.com',cerceve:'Var',alt_yazi:'MENÜ'}).ok,
  qr_bayt:P('qr',{metin:'ş'.repeat(76),cerceve:'Yok'}).ok,
  qr_satirli:P('qr',{metin:'a\nb',cerceve:'Yok'}).ok,
  yapboz_ok:P('yapboz',{parca:'30'}).ok,
  yapboz_kotu:P('yapboz',{parca:'31'}).ok
};
process.stdout.write(JSON.stringify(o));
"""


def manifest_vakalari():
    s = {}
    p = subprocess.run(["node", "-e", NODE_MANIFEST, os.path.join(KOK, "foto-uretim-veri.js")], capture_output=True,
                       text=True)
    if p.returncode != 0:
        return {"V0": (False, "node: " + p.stderr[-300:])}
    m = json.loads(p.stdout)
    tur = {t["kod"]: t for t in m["turler"]}
    hata = []
    for kod, (ad, girdi, uretec, az, cok, bolgeler, malz, notu, durust) in G2_SATIR.items():
        t = tur.get(kod) or {}
        bekle = {"ad": ad, "girdi": girdi, "motor": "D", "uretec": uretec, "olcu_mm": {"en_az": az, "en_cok": cok},
                 "fiyat": {"formul": "mm_x_10tl", "adim_mm": 10, "taban_tl": 600, "ek_renk_tl": 100, "renk_tavani": 4}, "ornek_kanit_izni": ["baski", "render"]}
        for k, v in bekle.items():
            if t.get(k) != v:
                hata.append("%s.%s=%r" % (kod, k, t.get(k)))
        if [b.get("kod") for b in t.get("renk_bolgeleri") or []] != bolgeler:
            hata.append("%s.renk_bolgeleri" % kod)
        if list((t.get("malzemeler") or {}).values()) != [malz]:
            hata.append("%s.malzemeler" % kod)
        if not all(isinstance(a.get("etiket"), str) and a["etiket"] for a in (t.get("form") or {}).values()):
            hata.append("%s.form.etiket" % kod)
        if not t.get("form"):
            hata.append("%s.form-bos" % kod)
    s["V1"] = (not hata, "satir: %s" % (hata or "6/6"))
    hata = [k for k, x in G2_SATIR.items() if (tur.get(k) or {}).get("ornek_notu") != x[7] or
            (tur.get(k) or {}).get("durustluk") != x[8]]
    bos = [t["kod"] for t in m["turler"] if not t.get("ornek_notu") or not t.get("durustluk")]
    s["V2"] = (not hata and not bos, "metin farki=%s bos=%s" % (hata, bos))
    adlar = sorted({r for t in m["turler"] for b in t.get("renk_bolgeleri") or [] for r in b.get("renkler") or []})
    disarida = [a for a in adlar if a not in m["renk_hex"]]
    s["V3"] = (m["renk_hex"] == RENK_HEX_KARAR and not disarida, "RENK_HEX=%s tabloda-yok=%s" % (
        m["renk_hex"] == RENK_HEX_KARAR, disarida))
    yanlis = [k for k in G2_SATIR if m["tarayici"].get(tur.get(k, {}).get("uretec")) or m["kol"].get(k) != "deterministik"]
    # G2b: her G2 turunun TAM BIR render ornegi var; adres foto/ornek/<kod>-1-render.webp (R2 pruvo-media).
    ornek = {}
    for t_, r_, o_ in m["ornek_render"]:
        ornek.setdefault(t_, []).append((r_, o_))
    eksik = [k for k in G2_SATIR if ornek.get(k) != [("https://media.pruvo3d.com/foto/ornek/%s-1-render.webp" % k,) * 2]]
    s["V4"] = (not yanlis and not eksik, "tarayici/kol yanlis=%s render-ornegi-eksik/yanlis=%s" % (yanlis, eksik))
    # Tek onay kutusu (taslak-2, 7 Eki 20:5x): ayri hak/aktarim metni ve kutu kurali YOK; onay = aydinlatma listesi.
    s["V5"] = (m["onay_anahtar"] == ["aydinlatma"] and m["hak_fn"] == "undefined/undefined"
               and m["onay_surum"] == "2026-10-07-taslak-2",
               "onay_anahtar=%s hak_fn=%s onay_surum=%s" % (m["onay_anahtar"], m["hak_fn"], m["onay_surum"]))
    mod = kosucu_modulu()
    eksik = [kod for _, kod in mod.RET_KALIPLARI if kod not in m["red"]]
    kopru_kod = ["kisa-kenar", "qr-uzun"]
    eksik += [k for k in kopru_kod if k not in m["red"]]
    ret_ok = (mod.ret_kodu("RET: plaka/QR renk kontrasti 1.80 < 4.5 (acik/koyu cift sec)") == "kontrast" and
              mod.ret_kodu("RET: parca kisa kenari 18.0 mm < 24 mm: satir/sutun sayisini azaltin") == "parca" and
              mod.ret_kodu("RET: en ince cizgi 0.512 mm < 0.8 mm (yaziyi buyut: plakayi buyut)") == "metin-sigmadi" and
              mod.ret_kodu("RET: SVG: desteklenmeyen eleman <text> (metin/filter/gorsel/maske/stil yok)") == "svg" and
              mod.ret_kodu("RET: bilinmeyen alan: x") == "genel")
    s["V6"] = ("renkler birbirine çok yakın" in m["red_kontrast"] and m["red_bilinmez"] == m["red"][""] and
               m["red_genel"] == m["red"][""] and not eksik and ret_ok,
               "kontrast=%r eksik=%s ret_kodu=%s" % (m["red_kontrast"][:50], eksik, ret_ok))
    pp = m["p"]
    s["V7"] = (pp["isim_ok"] and not pp["isim_4satir"] and not pp["isim_41"] and not pp["isim_bos_satir"] and
               not pp["isim_secim"] and pp["qr_altsiz"]["ok"] and "alt_yazi" not in pp["qr_altsiz"]["deger"] and
               pp["qr_alt"] and not pp["qr_bayt"] and not pp["qr_satirli"] and pp["yapboz_ok"] and
               not pp["yapboz_kotu"], "parametreDogrula=%s" % json.dumps(pp, ensure_ascii=False))
    # V8: her form alaninin HER secenegi uretec semasina eslenir (KopruRed yok, alanlar semada, olcu alani dogru).
    hata = []
    d = tempfile.mkdtemp(prefix="foto-kosucu-v8-")
    try:
        with open(os.path.join(d, "foto.png"), "wb") as f:
            f.write(png_gri(8, 8))
        with open(os.path.join(d, "svg.svg"), "w", encoding="utf-8") as f:
            f.write(SVG_ORNEK)
        tablo = mod.cli_tablosu()
        for kod in G2_SATIR:
            t = tur[kod]
            gtab = tablo.get(t["uretec"]) or {}
            fn = mod.ESLEMELER.get(gtab.get("esle"))
            if gtab.get("bicim") != "tekin-ortak" or not fn:
                hata.append("%s:tablo" % kod)
                continue
            taban = {}
            for a, sema in t["form"].items():
                taban[a] = {"sayi": sema.get("min"), "secim": (sema.get("secenekler") or [None])[0],
                            "metin": "Ada", "url": "https://pruvo3d.com"}[sema["tip"]]
            denemeler = [dict(taban)]
            for a, sema in t["form"].items():
                for sec in sema.get("secenekler") or []:
                    denemeler.append(dict(taban, **{a: sec}))
            for p_ in denemeler:
                girdi = {"sozlesme": 1, "kategori": kod, "olcu_mm": t["olcu_mm"]["en_cok"],
                         "renkler": {b["kod"]: b["renkler"][0] for b in t["renk_bolgeleri"]},
                         "parametreler": p_, "dosyalar": {"foto": "foto.png", "svg": "svg.svg"}}
                try:
                    u, bolgeler = fn(girdi, d, m["renk_hex"])
                except mod.KopruRed as e:
                    hata.append("%s:%s->%s" % (kod, json.dumps(p_, ensure_ascii=False), e.kod))
                    continue
                if not set(u) <= URETEC_ALANLARI[kod] or u.get(URETEC_OLCU_ALANI[kod]) != float(t["olcu_mm"]["en_cok"]):
                    hata.append("%s:alan %s" % (kod, sorted(set(u) - URETEC_ALANLARI[kod])))
                if not set(bolgeler) <= {b["kod"] for b in t["renk_bolgeleri"]}:
                    hata.append("%s:bolge" % kod)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    s["V8"] = (not hata, "esleme: %s" % (hata or "6/6 tur, her secenek"))
    # V9 (G2b): plaka siniri TEK kaynak manifest PLAKA_MM=300; kosucu ayni degeri okur (ikinci kopya yok).
    try:
        km = kosucu_modulu().plaka_mm()
    except SystemExit as e:
        km = "DUR: %s" % e
    s["V9"] = (m["plaka"] == 300 and km == 300, "manifest=%s kosucu=%s" % (m["plaka"], km))
    return s


# ------------------------------------------------------------------ GERCEK uretec (CI DISI, G2)
def _png_sekil(w, h, siyah):
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ham = b"".join(b"\0" + bytes(0 if siyah(x, y) else 255 for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b""))


def _halka_ucgen(x, y):
    """Geometrik silüet (logo/marka DEGIL): halka + ucgen."""
    r2 = (x - 200) ** 2 + (y - 200) ** 2
    halka = 60 ** 2 <= r2 <= 140 ** 2
    ucgen = 400 <= x <= 580 and abs(y - 200) <= (x - 400) * 0.75
    return halka or ucgen


def _halka(x, y):
    r2 = (x - 200) ** 2 + (y - 150) ** 2
    return 50 ** 2 <= r2 <= 130 ** 2


def _foto_ton(w, h):
    """Sentetik ton fotografi (gradyan + acik daire): kisi/marka YOK."""
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    satirlar = []
    for y in range(h):
        satirlar.append(b"\0" + bytes(230 if (x - w // 2) ** 2 + (y - h // 2) ** 2 < (h // 5) ** 2
                                      else int(40 + 180 * x / w * (1 - y / (2.0 * h))) for x in range(w)))
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(b"".join(satirlar))) + ch(b"IEND", b""))


def gercek_vakalar():
    siluet = ("foto.png", _png_sekil(600, 400, _halka_ucgen))
    halka = ("foto.png", _png_sekil(400, 300, _halka))
    foto = ("foto.png", _foto_ton(640, 480))
    svg = ("svg.svg", SVG_ORNEK.encode())
    v = []
    for olcu, kisa, sat in ((60, 20, "Ada"), (155, 60, "Deniz Yılmaz\nDaire 4"), (250, 100, "Deniz Yılmaz\nDaire 4\nKat 2")):
        v.append(("isimlik", olcu, {"plaka": "Beyaz", "yazi": "Lacivert"},
                  {"satirlar": sat, "kisa_kenar_mm": kisa, "yazi_tipi": "Düz", "plaka_sekli": "Yuvarlak köşe",
                   "montaj_delikleri": "Var" if olcu > 60 else "Yok"}, {}))
    for olcu, ek in ((40, {"cerceve": "Yok"}), (95, {"cerceve": "Var"}), (150, {"cerceve": "Var", "alt_yazi": "MENÜ"})):
        v.append(("qr", olcu, {"plaka": "Beyaz", "kod": "Siyah"}, dict({"metin": "https://pruvo3d.com"}, **ek), {}))
    for olcu, taban in ((30, "Yok"), (115, "Var"), (200, "Var")):
        v.append(("logo", olcu, {"taban": "Beyaz", "logo": "Kırmızı"}, {"taban": taban}, {"svg": svg}))
    for olcu, sap in ((20, "Silindir"), (60, "Topuz"), (100, "Silindir")):
        v.append(("muhur", olcu, {"govde": "Mavi", "sap": "Beyaz"}, {"sap": sap}, {"foto": siluet}))
    for olcu, mod, gor in ((60, "Delikli", siluet), (155, "Dolu silüet", halka), (250, "Delikli", siluet)):
        v.append(("sablon", olcu, {"sablon": "Gri"}, {"mod": mod}, {"foto": gor}))
    for olcu, parca in ((100, "12"), (150, "20"), (190, "30")):
        v.append(("yapboz", olcu, {"yapboz": "Ahşap"}, {"parca": parca}, {"foto": foto}))
    return v


def uc_mf_kutular(yol):
    """3MF'ten BAGIMSIZ olcum: {nesne adi: (min xyz, max xyz)} dunya koordinatinda (component + build donusumu)."""
    z = zipfile.ZipFile(yol)
    xml = z.read([n for n in z.namelist() if n.endswith(".model")][0]).decode()
    nesne = {}
    for m in re.finditer(r'<object\b([^>]*)>(.*?)</object>', xml, re.S):
        oid = re.search(r'\bid="(\d+)"', m.group(1)).group(1)
        ad = (re.search(r'\bname="([^"]*)"', m.group(1)) or [None, oid])[1]
        vs = [tuple(float(c) for c in t) for t in re.findall(
            r'<vertex x="([-0-9.e]+)" y="([-0-9.e]+)" z="([-0-9.e]+)"', m.group(2))]
        komp = [(c.group(1), c.group(2)) for c in re.finditer(
            r'<component\b[^>]*objectid="(\d+)"(?:[^>]*transform="([^"]*)")?', m.group(2))]
        nesne[oid] = (ad, vs, komp)

    def donustur(p, t):
        if not t:
            return p
        a = [float(x) for x in t.split()]
        return (p[0] * a[0] + p[1] * a[3] + p[2] * a[6] + a[9], p[0] * a[1] + p[1] * a[4] + p[2] * a[7] + a[10],
                p[0] * a[2] + p[1] * a[5] + p[2] * a[8] + a[11])

    def noktalar(oid, t=None):
        ad, vs, komp = nesne[oid]
        out = [donustur(p, t) for p in vs]
        for cid, ct in komp:
            out += [donustur(p, t) for p in noktalar(cid, ct)]
        return out

    kutu = {}
    for b in re.finditer(r'<item\b[^>]*objectid="(\d+)"(?:[^>]*transform="([^"]*)")?', xml):
        ps = noktalar(b.group(1), b.group(2))
        if ps:
            kutu[nesne[b.group(1)][0]] = (tuple(min(p[i] for p in ps) for i in range(3)),
                                          tuple(max(p[i] for p in ps) for i in range(3)))
    return kutu


def gercek(json_yolu=None):
    import time
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    mod = kosucu_modulu()
    satirlar, gecen = [], 0
    for kod, olcu, renkler, par, dosyalar in gercek_vakalar():
        o = Ortam(tablo=False)
        try:
            o.env["FOTO_KOSUCU_JENERATOR"] = jen
            o.env["FOTO_KOSUCU_PYTHON"] = py
            d = o.uretec_onizleme(kod, olcu, renkler, par, dosyalar)
            t0 = time.time()
            rc, son, cikti = o.kos("--uygula")
            sure = time.time() - t0
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            olcu_j = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
            px = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24]) \
                if os.path.isfile(os.path.join(d, "onizleme.png")) else (0, 0)
            bag, birim, sha_ayni = None, None, None
            if os.path.isfile(os.path.join(d, "model.3mf")):
                birim = re.search(r'unit="([a-z]+)"', zipfile.ZipFile(os.path.join(d, "model.3mf")).read(
                    "3D/3dmodel.model").decode()).group(1)
                kutular = uc_mf_kutular(os.path.join(d, "model.3mf"))
                if kod == "yapboz":
                    # Parcalar tablada raf duzeninde: birlesik plaket = 3MF konumu - ozet.parcalar[].tasima_mm.
                    # ozet uretec ayni girdiyle YENIDEN kosularak alinir (determinizm: model sha esit olmali).
                    g = json.load(open(os.path.join(d, "girdi.json"), encoding="utf-8"))
                    u, _ = mod.ESLEMELER["yapboz"](g, d, mod.renk_tablosu())
                    td = tempfile.mkdtemp(prefix="foto-kosucu-gercek-")
                    try:
                        with open(os.path.join(td, "u.json"), "w", encoding="utf-8") as f:
                            json.dump(u, f, ensure_ascii=False, sort_keys=True)
                        subprocess.run([py, os.path.join(jen, "jeneratorler/foto/yapboz_uret.py"), "--girdi",
                                        os.path.join(td, "u.json"), "--cikti", os.path.join(td, "c")],
                                       capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
                        oz = json.load(open(os.path.join(td, "c", "ozet.json")))
                        sha_ayni = open(os.path.join(td, "c", "uretec.3mf"), "rb").read() == \
                            open(os.path.join(d, "model.3mf"), "rb").read()
                    finally:
                        shutil.rmtree(td, ignore_errors=True)
                    tas = {p["ad"]: p["tasima_mm"] for p in oz.get("parcalar", [])}
                    mn = [min(k[0][i] - tas[a][i] for a, k in kutular.items()) for i in (0, 1)]
                    mx = [max(k[1][i] - tas[a][i] for a, k in kutular.items()) for i in (0, 1)]
                    bag = max(mx[0] - mn[0], mx[1] - mn[1])
                else:
                    mn = [min(k[0][i] for k in kutular.values()) for i in (0, 1)]
                    mx = [max(k[1][i] for k in kutular.values()) for i in (0, 1)]
                    bag = max(mx[0] - mn[0], mx[1] - mn[1])
            uk = olcu_j.get("uzun_kenar_mm")
            ok = (r["asama"] == "onizleme-hazir" and olcu_j.get("sizdirmaz") is True and birim == "millimeter" and
                  isinstance(uk, (int, float)) and abs(uk - olcu) <= olcu * 0.01 and
                  bag is not None and abs(bag - olcu) <= olcu * 0.01 and max(px) >= 1024 and
                  1 <= (olcu_j.get("renk_sayisi") or 0) <= 4 and sha_ayni is not False)
            gecen += 1 if ok else 0
            satirlar.append({"kod": kod, "olcu": olcu, "hukum": "GECTI" if ok else "KIRMIZI", "asama": r["asama"],
                             "hata": r["hata"], "sizdirmaz": olcu_j.get("sizdirmaz"), "uzun_kenar_mm": uk,
                             "bagimsiz_uzun_kenar_mm": round(bag, 3) if bag is not None else None,
                             "sapma_yuzde": round(abs(bag - olcu) / olcu * 100, 3) if bag is not None else None,
                             "kutu_mm": olcu_j.get("kutu_mm"), "renk_sayisi": olcu_j.get("renk_sayisi"),
                             "onizleme_px": list(px), "sure_sn": round(sure, 1), "ucgen": olcu_j.get("ucgen"),
                             "parametreler": par, "uretec_rc_ozet": "" if ok else cikti.strip()[-300:]})
            print("%s %-7s %3d asama=%s hata=%s sizdirmaz=%s uk=%s bagimsiz=%s renk=%s px=%s %.1fs" % (
                "✅" if ok else "❌", kod, olcu, r["asama"], r["hata"] or "-", olcu_j.get("sizdirmaz"), uk,
                round(bag, 3) if bag is not None else None, olcu_j.get("renk_sayisi"), px, sure))
        finally:
            o.kapat()
    print("GERCEK_KOSUM=%d/%d" % (gecen, len(satirlar)))
    if json_yolu:
        with open(json_yolu, "w", encoding="utf-8") as f:
            json.dump(satirlar, f, ensure_ascii=False, indent=1)
    return 0 if gecen == len(satirlar) else 1


def main():
    if "--uctan-uca" in sys.argv:
        return uctan_uca()
    if "--gercek" in sys.argv:
        a = sys.argv
        return gercek(a[a.index("--json") + 1] if "--json" in a else None)
    kirmizi = 0
    for ad, (g, ac) in manifest_vakalari().items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:400]))
        kirmizi += 0 if g else 1
    for ad, (g, ac) in vakalar(KOSUCU).items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:300]))
        kirmizi += 0 if g else 1
    survivor = 0
    # SURE (8 Eki 2026: seri 273 sn, pre-push ayna tavani 300 sn): mutantlar PARALEL kosar. Her mutant kendi
    # tempfile agacinda + her vaka kendi Ortam'inda (ayri SQLite/R2/kilit) -> paylasilan durum yok; anlam AYNI.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as h:
        sonuclar = list(h.map(mutant_kos, list(MUTANTLAR)))
    for ad, (g, ac) in zip(MUTANTLAR, sonuclar):
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
        survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())
