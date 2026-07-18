#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel canli parity panel HTTP sunucusu."""

import importlib.util
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PANEL = "/Users/okan/dev/pruvo/tools/parity-panel.py"
HOST = "127.0.0.1"
PORT = 8137


def load_panel_module():
    spec = importlib.util.spec_from_file_location("parity_panel_runtime", PANEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            module = load_panel_module()
            html = module.render_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        except Exception:
            body = traceback.format_exc().encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print("PARITY PANEL: http://127.0.0.1:8137")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
