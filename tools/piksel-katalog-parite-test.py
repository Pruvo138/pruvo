#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PIKSEL ↔ KATALOG PARITE KAPISI — Meta/Google katalog feed g:id ile tarayici/CAPI pikselinin
gonderdigi content_ids AYNI KURALDAN (feed_id) turer mi?

NEDEN VAR (olculdu, 21 Tem): katalog feed'i (merchant-feed.xml) uzun urun id'sini <=50 karaktere
kisaltir (build.feed_id: uzunsa ilk 41 + '-' + sha1[:8]); oysa piksel content_ids TAM pid
gonderiyordu. Sonuc: id'si 50 karakteri asan 610/7769 urunde (%7,85) piksel content_id katalogdaki
g:id ile ESLESMIYOR -> Advantage+ katalog reklami o urunleri KOR gosteriyor (yanlis/eslesmeyen
urun). OLCULEN eslesme orani (duzeltme ONCESI): %92,15.

DUZELTME: content_ids ureten HER YUZEY feed_id'den turetir:
  * tools/build.py  render_product : ViewContent content_ids = feed_id(pid); urun_json.fid=feed_id;
                                     AddToCart content_ids = URUN.fid
  * index.html      InitiateCheckout/Purchase : pruvoFeedId(satir.id)  (feed_id JS port)
  * shop/src/olcum.js CAPI Purchase           : feedId(item_id)        (feed_id JS uc port)
Sepet satir id'si (satir.id / item_id) TAM pid KALIR — Worker/D1 fiyat anahtari; donusum yalniz
Meta olayina cikarken uygulanir.

BU TESTIN OLCTUGU:
  A) SABLON PARITESI (pure-python, CI-bloklayici): feed-uygun her urun icin render_product'in
     URETTIGI ViewContent content_ids == feed_id(pid) mi? feed id kumesi ↔ sablon content_ids
     kumesi parite orani < esik -> exit 1. (Ayrica AddToCart URUN.fid + urun_json.fid dogrulanir.)
  B) JS UC PARITESI (node varsa; CI Python-only ise ATLANIR, FAIL degil): index.html pruvoFeedId
     ve shop/src/olcum.js feedId, Python feed_id ile TUM uzun-id'lerde BYTE-BIRE-BIR ayni mi?

Kullanim:
    python3 tools/piksel-katalog-parite-test.py           # bayraksiz: parite tam ise exit 0
    python3 tools/piksel-katalog-parite-test.py --esik 99  # esik yuzdesi (varsayilan 100)
    python3 tools/piksel-katalog-parite-test.py --olcum    # yalniz ONCE/SONRA olcum raporu

KIRMIZI-MUTASYON: build.py'de ViewContent content_ids'i feed_id(pid) yerine pid'e ceviren TEK
SATIRLIK mutasyon -> uzun-id urunlerde sablon != feed -> parite duser -> exit 1 (git archive ile
izole kopyada kanitlanir).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build as B  # noqa: E402  feed_id / feed_price / images_of / render_product — TEK KAYNAK

URUNLER = os.path.join(ROOT, "urunler.json")
INDEX_HTML = os.path.join(ROOT, "index.html")
OLCUM_JS = os.path.join(ROOT, "shop", "src", "olcum.js")

# render_product'in bastigi ViewContent olayindan content_ids JSON literalini cek.
VC_RE = re.compile(r'pruvoMetaTrack\("ViewContent",\s*(\{.*?\})\s*\);')
URUN_JSON_RE = re.compile(r'var URUN = (\{.*?\});')


def feed_uygun(p):
    """render_merchant_feed KABUL kriterleri (build.py ile ayni): parametrik degil + sayisal
    fiyat + en az bir gorsel."""
    if p.get("parametrik"):
        return False
    if not B.feed_price((p.get("fiyat") or "").strip()):
        return False
    if not B.images_of(p):
        return False
    return True


def urunleri_yukle():
    with open(URUNLER, encoding="utf-8") as f:
        return json.load(f)


def sablon_content_id(urun, tum):
    """render_product'i cagirir, ViewContent content_ids listesini dondurur (yoksa None)."""
    html = B.render_product(urun, tum)
    m = VC_RE.search(html)
    if not m:
        return None, html
    try:
        veri = json.loads(m.group(1))
    except ValueError:
        return None, html
    return veri.get("content_ids"), html


# ----------------------------------------------------------------- A) SABLON PARITESI
def olc_sablon(urunler):
    """feed-uygun her urun icin (feed_id, sablon_content_id) uret; per-urun eslesme say."""
    feed_urunler = [p for p in urunler if feed_uygun(p)]
    eslesen, uyumsuz = 0, []
    for p in feed_urunler:
        pid = p["id"]
        fid = B.feed_id(pid)
        cids, _ = sablon_content_id(p, urunler)
        if cids == [fid]:
            eslesen += 1
        else:
            uyumsuz.append((pid, fid, cids))
    return feed_urunler, eslesen, uyumsuz


def olc_once(urunler):
    """DUZELTME ONCESI davranisi (piksel = TAM pid) yeniden uretir: kac urunde pid != feed_id?
    Salt-olcum — kaynagi render ETMEZ, kurali uygular (rapor icin)."""
    feed_urunler = [p for p in urunler if feed_uygun(p)]
    eslesen = sum(1 for p in feed_urunler if p["id"] == B.feed_id(p["id"]))
    return len(feed_urunler), eslesen


def addtocart_kontrol(urunler):
    """En az bir uzun-id (pid != feed_id) urunde render_product ciktisinda:
      - AddToCart content_ids = URUN.fid (TAM pid'e sabitlenmemis)
      - urun_json.fid == feed_id(pid)
    Bu, ViewContent disindaki sablon yuzeyini de nobet altina alir."""
    uzun = [p for p in urunler
            if feed_uygun(p) and p["id"] != B.feed_id(p["id"])]
    if not uzun:
        return True, "uzun-id feed urunu yok (kontrol atlanabilir)"
    p = uzun[0]
    html = B.render_product(p, urunler)
    fid = B.feed_id(p["id"])
    atc_ok = "content_ids:[URUN.fid]" in html
    mj = URUN_JSON_RE.search(html)
    fid_ok = False
    if mj:
        try:
            fid_ok = json.loads(mj.group(1)).get("fid") == fid
        except ValueError:
            fid_ok = False
    return (atc_ok and fid_ok), (
        "AddToCart URUN.fid=%s urun_json.fid=%s (pid=%s)" % (atc_ok, fid_ok, p["id"]))


# ----------------------------------------------------------------- B) JS UC PARITESI (node)
def _node_var():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _index_feedid_blok():
    """index.html'den BEGIN/END pruvoFeedId isaretli JS blogundaki FONKSIYON TANIMLARINI cek
    (acilis yorumunu haric tut; ilk 'function pruvoSha1Hex'ten END isaretine kadar)."""
    with open(INDEX_HTML, encoding="utf-8") as f:
        metin = f.read()
    m = re.search(r"BEGIN pruvoFeedId.*?(function pruvoSha1Hex.*?)/\* ===== END pruvoFeedId",
                  metin, re.S)
    return m.group(1) if m else None


def js_parite(uzun_pidler):
    """olcum.js feedId + index.html pruvoFeedId'i node ile uzun_pidler uzerinde kosar; Python
    feed_id ile karsilastirir. (ok, mesaj) dondurur. node yoksa (None, 'atlandi')."""
    if not _node_var():
        return None, "node yok -> JS uc paritesi ATLANDI (CI Python-only; yerelde node ile kosun)"
    beklenen = {pid: B.feed_id(pid) for pid in uzun_pidler}
    blok = _index_feedid_blok()
    if blok is None:
        return False, "index.html'de BEGIN/END pruvoFeedId isareti bulunamadi"

    veri_json = json.dumps(uzun_pidler, ensure_ascii=False)
    # Tek node harness: hem olcum.js feedId'i import eder hem index.html blogunu satir-ici kullanir.
    harness = (
        'import { feedId as olcumFeedId } from ' + json.dumps(OLCUM_JS) + ';\n'
        + blok + '\n'
        + 'const pidler = ' + veri_json + ';\n'
        + 'const cikti = {};\n'
        + 'for (const pid of pidler) { cikti[pid] = { olcum: olcumFeedId(pid), '
          'index: pruvoFeedId(pid) }; }\n'
        + 'process.stdout.write(JSON.stringify(cikti));\n'
    )
    tmp = tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8")
    try:
        tmp.write(harness)
        tmp.close()
        r = subprocess.run(["node", tmp.name], capture_output=True, text=True)
        if r.returncode != 0:
            return False, "node harness patladi: " + (r.stderr.strip() or "?")
        try:
            js = json.loads(r.stdout)
        except ValueError:
            return False, "node ciktisi JSON degil: " + r.stdout[:200]
    finally:
        os.unlink(tmp.name)

    hatali = []
    for pid, bekle in beklenen.items():
        g = js.get(pid, {})
        if g.get("olcum") != bekle:
            hatali.append("olcum.js feedId(%s)=%s != %s" % (pid, g.get("olcum"), bekle))
        if g.get("index") != bekle:
            hatali.append("index.html pruvoFeedId(%s)=%s != %s" % (pid, g.get("index"), bekle))
    if hatali:
        return False, "%d JS uc sapmasi (ilk: %s)" % (len(hatali), hatali[0])
    return True, "olcum.js + index.html JS uc: %d uzun-id'de Python feed_id ile birebir" % len(uzun_pidler)


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esik", type=float, default=100.0,
                    help="sablon paritesi alt esigi (%%). Varsayilan 100 (feed==sablon).")
    ap.add_argument("--olcum", action="store_true",
                    help="yalniz ONCE/SONRA olcum raporu bas, testi kosma")
    args = ap.parse_args()

    urunler = urunleri_yukle()
    toplam = len(urunler)
    parametrik = sum(1 for p in urunler if p.get("parametrik"))

    # --- ONCE (duzeltme oncesi: piksel = TAM pid) ---
    feed_n, once_eslesen = olc_once(urunler)
    once_oran = 100.0 * once_eslesen / feed_n if feed_n else 0.0

    if args.olcum:
        print("OLCUM (kaynak render ETMEDEN, kural uygulanarak)")
        print("  Toplam urun            : %d" % toplam)
        print("  Parametrik (sari seri) : %d" % parametrik)
        print("  Feed-uygun urun        : %d" % feed_n)
        print("  ONCE (piksel=TAM pid)  : %d eslesen  -> %.2f%%" % (once_eslesen, once_oran))
        print("  Uyumsuz (id>50 char)   : %d" % (feed_n - once_eslesen))
        return 0

    # --- SONRA: SABLON paritesi (render_product'tan gercek content_ids) ---
    feed_urunler, eslesen, uyumsuz = olc_sablon(urunler)
    sonra_oran = 100.0 * eslesen / len(feed_urunler) if feed_urunler else 0.0

    # --- AddToCart + urun_json.fid nobetcisi ---
    atc_ok, atc_msg = addtocart_kontrol(urunler)

    # --- B) JS uc paritesi (uzun-id kumesi uzerinde) ---
    uzun_pidler = sorted(p["id"] for p in feed_urunler if p["id"] != B.feed_id(p["id"]))
    js_ok, js_msg = js_parite(uzun_pidler)

    # ---- rapor ----
    print("PIKSEL ↔ KATALOG PARITE KAPISI")
    print("  Toplam urun / feed-uygun     : %d / %d" % (toplam, len(feed_urunler)))
    print("  Uzun-id (pid != feed_id)     : %d" % len(uzun_pidler))
    print("  ONCE (piksel=TAM pid)        : %.2f%%  (%d eslesmez)" % (once_oran, feed_n - once_eslesen))
    print("  SONRA sablon paritesi        : %.2f%%  (%d/%d)  [esik %.1f%%]"
          % (sonra_oran, eslesen, len(feed_urunler), args.esik))
    print("  AddToCart/urun_json.fid      : %s — %s" % ("OK" if atc_ok else "FAIL", atc_msg))
    if js_ok is None:
        print("  JS uc paritesi (B)           : ATLANDI — %s" % js_msg)
    else:
        print("  JS uc paritesi (B)           : %s — %s" % ("OK" if js_ok else "FAIL", js_msg))
    if uyumsuz:
        print("  --- SABLON UYUMSUZLARI (ilk 10) ---")
        for pid, fid, cids in uyumsuz[:10]:
            print("    pid=%s  feed_id=%s  sablon=%s" % (pid, fid, cids))
    print("-" * 70)

    kirmizi = []
    if sonra_oran < args.esik:
        kirmizi.append("sablon paritesi %.2f%% < esik %.1f%%" % (sonra_oran, args.esik))
    if not atc_ok:
        kirmizi.append("AddToCart/urun_json.fid nobetcisi: " + atc_msg)
    if js_ok is False:
        kirmizi.append("JS uc paritesi: " + js_msg)

    if kirmizi:
        for h in kirmizi:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅  — feed g:id ile sablon content_ids TEK KAYNAK (feed_id).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
