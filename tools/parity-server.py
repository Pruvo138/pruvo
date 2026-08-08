#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel canli parity panel HTTP sunucusu (LaunchAgent: com.pruvo.parity-panel).

/      -> panel HTML (her GET'te modul YENIDEN yuklenir; kod+veri TAZE)
/veri  -> panelin AYNI panel_data() ciktisi, JSON. Sayfa bunu periyodik fetch eder;
          <meta refresh> KULLANILMAZ (arama/filtre/siralama sifirlanmasin).

FAIL-LOUD: port 8137'yi baskasi (or. elle acilmis `python -m http.server`) tutuyorsa
bind hatasi ACIK mesajla log'a yazilir. Sessiz cikis KABUL EDILMEZ: KeepAlive=true ile
sessiz cokme sonsuz yeniden-baslatma dongusu demektir ve panel "calisiyor" sanilir.
"""

import errno
import importlib.util
import json
import socket
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import os

PANEL = os.environ.get("PRUVO_PARITY_PANEL", "/Users/okan/dev/pruvo/tools/parity-panel.py")
HOST = "127.0.0.1"
# Canli servis DAIMA 8137. Ortam degiskeni yalnizca KABUL TESTI icindir: canli paneli
# durdurmadan ayri bir portta uctan uca (/ ve /veri) olcebilmek icin.
PORT = int(os.environ.get("PRUVO_PARITY_PORT", "8137"))


def load_panel_module():
    spec = importlib.util.spec_from_file_location("parity_panel_runtime", PANEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Handler(BaseHTTPRequestHandler):
    def _gonder(self, kod, tur, govde):
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        yol = self.path.split("?", 1)[0].rstrip("/") or "/"
        try:
            module = load_panel_module()
            if yol in ("/veri", "/veri.json"):
                self._gonder(200, "application/json; charset=utf-8",
                             module.veri_json().encode("utf-8"))
                return
            if yol not in ("/", "/index.html"):
                self._gonder(404, "text/plain; charset=utf-8", b"yok\n")
                return
            self._gonder(200, "text/html; charset=utf-8",
                         module.render_html().encode("utf-8"))
        except Exception:
            iz = traceback.format_exc()
            if yol in ("/veri", "/veri.json"):
                self._gonder(500, "application/json; charset=utf-8",
                             json.dumps({"hata": iz}, ensure_ascii=False).encode("utf-8"))
            else:
                self._gonder(500, "text/plain; charset=utf-8", iz.encode("utf-8"))

    def log_message(self, format, *args):
        return


def _kim_tutuyor():
    """Port dolu mu (teshis icin) — sadece bilgi amacli."""
    s = socket.socket()
    s.settimeout(1.0)
    try:
        s.connect((HOST, PORT))
        return True
    except Exception:
        return False
    finally:
        s.close()


def main():
    try:
        srv = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, errno.EACCES):
            print("HATA: %s:%d BAGLANAMADI (%s)." % (HOST, PORT, e.strerror), flush=True)
            print("      Portu BASKA bir surec tutuyor (canli yanit: %s)."
                  % ("VAR" if _kim_tutuyor() else "YOK"), flush=True)
            print("      Teshis:  lsof -i :%d" % PORT, flush=True)
            print("      KeepAlive=true oldugu icin bu surec yeniden baslatilacak ve", flush=True)
            print("      port bosalmadikca AYNI hatayi verecek. Cakisan sureci kapat.", flush=True)
            # KeepAlive firtinasini yavaslat (saniyede onlarca yeniden baslatma olmasin)
            time.sleep(30)
            sys.exit(2)
        raise
    print("PARITY PANEL: http://%s:%d  (veri ucu: /veri)" % (HOST, PORT), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
