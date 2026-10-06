#!/usr/bin/env python3
"""PRUVO shop testleri — GERCEK SQLite koprusu (D1 sahtesi YERINE gercek SQL).

Node testi bu sureci baslatir ve stdin'e satir satir JSON yazar:
    {"sql": "...", "binds": [...], "mod": "all" | "first" | "run" | "exec"}
Her istege TEK satir JSON cevap doner:
    {"results": [...], "meta": {"changes": n}}   ya da   {"error": "..."}

Veritabani bellekte kurulur ve sema KANONIK dosyadan okunur (tools/d1-sema.sql) —
testte elle yazilmis ikinci bir sema YOKTUR: kanondan bir kolon/tablo duserse SQL
"no such column/table" ile patlar ve test kirmizi yanar.

Stdlib disinda bagimlilik yok; ag yok. Varsayilan :memory:; `SQLITE_KOPRU_DB` verilirse o dosya
(yalniz uctan uca prova: koşucu ayni dosyayi okur; dosya testin GECICI dizinindedir).
"""
import json
import os
import sqlite3
import sys

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")


def kur():
    db = sqlite3.connect(os.environ.get("SQLITE_KOPRU_DB") or ":memory:")
    db.row_factory = sqlite3.Row
    with open(SEMA, encoding="utf-8") as f:
        db.executescript(f.read())
    return db


def cevap(veri):
    sys.stdout.write(json.dumps(veri, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    try:
        db = kur()
    except Exception as e:  # sema kurulamadi -> ilk istekte hata doner
        cevap({"error": "SEMA KURULAMADI: %s" % e})
        return 3
    cevap({"hazir": True})
    for satir in sys.stdin:
        satir = satir.strip()
        if not satir:
            continue
        try:
            istek = json.loads(satir)
            mod = istek.get("mod", "all")
            if mod == "exec":
                db.executescript(istek["sql"])
                db.commit()
                cevap({"results": [], "meta": {"changes": 0}})
                continue
            cur = db.execute(istek["sql"], istek.get("binds") or [])
            satirlar = [dict(r) for r in cur.fetchall()] if cur.description else []
            db.commit()
            cevap({"results": satirlar, "meta": {"changes": cur.rowcount if cur.rowcount > 0 else 0}})
        except Exception as e:
            cevap({"error": str(e)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
