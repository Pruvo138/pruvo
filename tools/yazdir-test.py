#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAZDIR.PY KABUL TESTLERI.

    python3 tools/yazdir-test.py

SAHTE yonetim API'si (yerel http.server, port 0) + sahte kucuk STL icerikleriyle
tools/yazdir.py'yi ucdan uca dogrular. GERCEK canliya (pruvo3d.com) BAGLANMAZ,
GERCEK Bambu Studio ACMAZ (yazdir.subprocess.run recorder ile mock'lanir).

Kabul (tools yazdir paketi):
  (a) normal urun siparisi -> parcalar dogru klasore indi + fis MALZEME/RENK/
      baski onerisi gosteriyor + --sadece-indir'de Bambu ACILMADI (subprocess.run
      cagrilmadigini dogrula) + exit 0.
  (b) dosyasi olmayan kalem -> "dosya yok: <id>" satiri + cokme yok + exit 0.
  (c) bilinmeyen siparis no -> net hata + exit != 0.
  (d) ANAHTAR ciktinin (stdout+stderr) hicbir yerinde gecmiyor.
  (e) parametrik (sari) kalem -> derleyici ucundan uretilip indi (server-side).
  (f) --sadece-indir DEGILSE Bambu acma denenir (subprocess.run cagrildi) —
      pozitif taraf (bambu app yolu mock'lanir).

Eski (arac yokken) senaryo: `import yazdir` ModuleNotFoundError = KIRMIZI kanit.
"""
import contextlib
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import yazdir  # noqa: E402  (yoksa import hatasi = once-kirmizi kanit)

ANAHTAR = "GIZLI-TEST-ANAHTAR-9c1f2a7b4e"  # ciktinin hicbir yerinde gorunmemeli

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("OK" if gecti else "FAIL", no, ad,
                                    (" | " + detay) if detay else ""), flush=True)


# --------------------------------------------------------------- sahte veri

STL_ICERIK = b"solid test\nfacet normal 0 0 0\nendsolid test\n"

SIPARISLER = {
    "PR-NORMAL-1": {
        "siparis_no": "PR-NORMAL-1",
        "tarih": "2026-07-17T09:30:00Z",
        "durum": "uretimde",
        "odeme_yontemi": "iyzico",
        "tutar_kurus": 85000, "kargo_kurus": 5000, "kdv_kurus": 15000,
        "musteri": {"ad": "Deniz Yilmaz", "tel": "0555 111 22 33",
                    "eposta": "d@example.com", "adres": "Fethiye Mah. 1 Sk. No:2"},
        "kalemler": [{
            "kalem": 0, "id": "test-normal-parca", "baslik": "Test Kelepce",
            "malzeme": "PETG", "renk": "Antrasit Gri", "adet": 2,
            "parametrik": False, "parametre_detay": "",
            "baski_oneri": "0.2 mm katman - %20 doluluk - 5 duvar",
            "stl_liste_ucu": "/api/shop/yonet/stl-liste?id=test-normal-parca",
        }],
    },
    "PR-EKSIK-1": {
        "siparis_no": "PR-EKSIK-1",
        "tarih": "2026-07-17T10:00:00Z",
        "durum": "uretimde", "odeme_yontemi": "iyzico",
        "tutar_kurus": 40000, "kargo_kurus": 5000, "kdv_kurus": 7000,
        "musteri": {"ad": "Ali Veli", "tel": "0555 000 00 00",
                    "eposta": "a@example.com", "adres": "Adres yok"},
        "kalemler": [{
            "kalem": 0, "id": "yok-urun", "baslik": "Dosyasiz Urun",
            "malzeme": "PLA", "renk": "Siyah", "adet": 1,
            "parametrik": False, "parametre_detay": "",
            "baski_oneri": "genel ayar",
            "stl_liste_ucu": "/api/shop/yonet/stl-liste?id=yok-urun",
        }],
    },
    "PR-SARI-1": {
        "siparis_no": "PR-SARI-1",
        "tarih": "2026-07-17T11:00:00Z",
        "durum": "uretimde", "odeme_yontemi": "iyzico",
        "tutar_kurus": 60000, "kargo_kurus": 5000, "kdv_kurus": 10000,
        "musteri": {"ad": "Ece Kaya", "tel": "0555 999 88 77",
                    "eposta": "e@example.com", "adres": "Sari Sok. No:3"},
        "kalemler": [{
            "kalem": 0, "id": "oring-uretici", "baslik": "O-ring (olcuye ozel)",
            "malzeme": "TPU", "renk": "Sari", "adet": 4,
            "parametrik": True, "parametre_detay": "ic cap 20mm, kesit 3mm",
            "baski_oneri": "esnek - yavas baski",
            "stl_ucu": "/api/shop/yonet/stl?siparis_no=PR-SARI-1&kalem=0",
        }],
    },
}

STL_LISTE = {
    "test-normal-parca": [
        {"dosya": "govde.stl", "boyut": len(STL_ICERIK)},
        {"dosya": "kapak.stl", "boyut": len(STL_ICERIK)},
    ],
    "yok-urun": [],  # bos -> dosya yok
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # sessiz

    def _json(self, kod, obj):
        govde = json.dumps(obj).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def _bytes(self, ad, veri):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % ad)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        # Anahtar HEADER'dan gelmeli (URL'de degil). Yanlissa 404 (varlik sizmasin).
        if self.headers.get("X-Yonet-Anahtar") != ANAHTAR:
            return self._json(404, {"hata": "bulunamadi"})
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/shop/yonet/liste":
            return self._json(200, {"siparisler": list(SIPARISLER.values())})
        if u.path == "/api/shop/yonet/stl-liste":
            urun = (q.get("id") or [""])[0]
            if urun not in STL_LISTE:
                return self._json(400, {"hata": "gecersiz-id"})
            parcalar = STL_LISTE[urun]
            govde = {"id": urun, "parcalar": parcalar}
            if not parcalar:
                govde["not"] = "dosya R2 stl/ prefix'inde yok (id: %s)" % urun
            return self._json(200, govde)
        if u.path == "/api/shop/yonet/stl":
            # Normal: id + dosya. Sari: siparis_no + kalem.
            if q.get("id") and q.get("dosya"):
                urun = q["id"][0]
                dosya = q["dosya"][0]
                parcalar = STL_LISTE.get(urun, [])
                if not any(p["dosya"] == dosya for p in parcalar):
                    return self._json(404, {"hata": "dosya-yok",
                                            "not": "listede yok (id: %s)" % urun})
                return self._bytes("PR-x-" + dosya, STL_ICERIK)
            if q.get("siparis_no") and q.get("kalem") is not None:
                # sari uretim (server-side derleme) — sahte STL don
                sn = q["siparis_no"][0]
                return self._bytes(sn + "-uretilen.stl", STL_ICERIK)
            return self._json(400, {"hata": "eksik-parametre"})
        return self._json(404, {"hata": "bulunamadi"})


def sunucu_baslat():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


# ------------------------------------------------------------------ kosum

def calistir(argv):
    """yazdir.main'i cagirir; (exit_kodu, stdout, stderr) doner.
    subprocess.run recorder ile mock'lanir (Bambu GERCEK acilmaz)."""
    cagrilar = []
    eski_run = yazdir.subprocess.run
    yazdir.subprocess.run = lambda *a, **k: cagrilar.append((a, k))
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            kod = yazdir.main(argv)
    finally:
        yazdir.subprocess.run = eski_run
    return kod, out.getvalue(), err.getvalue(), cagrilar


def main():
    srv, taban = sunucu_baslat()
    import tempfile
    tmp = tempfile.mkdtemp(prefix="yazdir-test-")
    tum_cikti = []

    # --- (a) normal + --sadece-indir ---
    k1 = os.path.join(tmp, "PR-NORMAL-1")
    kod, out, err, cagrilar = calistir(
        ["PR-NORMAL-1", "--taban", taban, "--anahtar", ANAHTAR,
         "--klasor", k1, "--sadece-indir"])
    tum_cikti.append(out); tum_cikti.append(err)
    govde_var = os.path.exists(os.path.join(k1, "01_govde.stl"))
    kapak_var = os.path.exists(os.path.join(k1, "01_kapak.stl"))
    kayit("a1", "normal parcalar dogru klasore indi",
          kod == 0 and govde_var and kapak_var,
          "kod=%s govde=%s kapak=%s" % (kod, govde_var, kapak_var))
    kayit("a2", "fis MALZEME/RENK/oneri gosteriyor",
          "PETG" in out and "Antrasit Gri" in out and "0.2 mm katman" in out)
    kayit("a3", "--sadece-indir: Bambu ACILMADI (subprocess.run cagrilmadi)",
          len(cagrilar) == 0, "cagri=%d" % len(cagrilar))

    # --- (b) dosyasi olmayan kalem ---
    k2 = os.path.join(tmp, "PR-EKSIK-1")
    kod, out, err, cagrilar = calistir(
        ["PR-EKSIK-1", "--taban", taban, "--anahtar", ANAHTAR,
         "--klasor", k2, "--sadece-indir"])
    tum_cikti.append(out); tum_cikti.append(err)
    kayit("b1", "dosya yok satiri + cokme yok + exit 0",
          kod == 0 and "dosya yok: yok-urun" in out,
          "kod=%s" % kod)

    # --- (c) bilinmeyen siparis no ---
    kod, out, err, cagrilar = calistir(
        ["PR-YOK-9999", "--taban", taban, "--anahtar", ANAHTAR,
         "--klasor", os.path.join(tmp, "yok"), "--sadece-indir"])
    tum_cikti.append(out); tum_cikti.append(err)
    kayit("c1", "bilinmeyen siparis -> net hata + exit != 0",
          kod != 0 and ("bulunamad" in (out + err)),
          "kod=%s" % kod)

    # --- (e) parametrik (sari) kalem ---
    k3 = os.path.join(tmp, "PR-SARI-1")
    kod, out, err, cagrilar = calistir(
        ["PR-SARI-1", "--taban", taban, "--anahtar", ANAHTAR,
         "--klasor", k3, "--sadece-indir"])
    tum_cikti.append(out); tum_cikti.append(err)
    sari_var = os.path.exists(os.path.join(k3, "01_oring-uretici.stl"))
    kayit("e1", "parametrik kalem server-side uretilip indi",
          kod == 0 and sari_var and "Sari" in out,
          "kod=%s dosya=%s" % (kod, sari_var))

    # --- (f) --sadece-indir DEGIL -> Bambu acma denenir ---
    k4 = os.path.join(tmp, "PR-NORMAL-1b")
    eski_yol = yazdir.bambu_uygulama_yolu
    yazdir.bambu_uygulama_yolu = lambda: "/Applications/Bambu Studio.app"  # zorla var
    kod, out, err, cagrilar = calistir(
        ["PR-NORMAL-1", "--taban", taban, "--anahtar", ANAHTAR, "--klasor", k4])
    yazdir.bambu_uygulama_yolu = eski_yol
    tum_cikti.append(out); tum_cikti.append(err)
    acildi = len(cagrilar) == 1 and "open" in cagrilar[0][0][0]
    kayit("f1", "--sadece-indir yok -> Bambu acma denendi (open cagrildi)",
          kod == 0 and acildi, "cagri=%d" % len(cagrilar))

    # --- (d) ANAHTAR hicbir ciktida gecmiyor ---
    hepsi = "".join(tum_cikti)
    kayit("d1", "ANAHTAR ciktinin hicbir yerinde gecmiyor",
          ANAHTAR not in hepsi)

    srv.shutdown()

    gecen = sum(1 for _, _, g in SONUC if g)
    print("\n%d/%d gecti" % (gecen, len(SONUC)))
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
