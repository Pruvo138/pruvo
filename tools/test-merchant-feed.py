#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kabul testi — Google Merchant feed g:id 50-karakter siniri (feed_id duzeltmesi).

GERCEK urunler.json'u yukler, build modulunu import eder, render_merchant_feed'i
calistirir, uretilen XML'i ayristirir ve sunu dogrular:
  (a) HICBIR g:id > 50 karakter DEGIL   (once-KIRMIZI: feed_id no-op yapilinca >50 goruluyor)
  (b) TUM g:id'ler global BENZERSIZ      (kisa + donusturulmus hepsi arasinda; cakisma yok)
  (c) kisa id'li (<=50) urunlerin g:id/g:mpn'i pid ile BIREBIR (korundu, churn yok)
  (d) <link> TAM pid iceriyor + <g:image_link> KAYNAK gorselle ayni (sayfa/URL degismedi)
  (e) item (urun) sayisi korunmus (feed_n = bagimsiz hesaplanan uygun urun sayisi)
Ek: feed_id birim testleri (tam 50 siniri, 51->50, deterministik).

Salt-okunur; dosyaya yazmaz, ag'a cikmaz. Cikis kodu: 0 = hepsi yesil, 1 = kirmizi.
Calistir:  python3 tools/test-merchant-feed.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import json
import build   # noqa: E402  (feed_id, render_merchant_feed, feed_price, images_of, product_url, esc, SITE)

FAILS = []


def check(label, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print("  [%s] %s%s" % (tag, label, ("  -> " + detail if detail else "")))
    if not cond:
        FAILS.append(label)
    return cond


# ---- item ayristirici (regex; id/mpn/link/image_link'in hepsi guvenli, escaped icerik yok) ----
_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)


def _tag(block, name):
    m = re.search(r"<%s>([^<]*)</%s>" % (re.escape(name), re.escape(name)), block)
    return m.group(1) if m else None


def parse_items(xml):
    out = []
    for block in _ITEM_RE.findall(xml):
        out.append({
            "id":   _tag(block, "g:id"),
            "mpn":  _tag(block, "g:mpn"),
            "link": _tag(block, "link"),
            "img":  _tag(block, "g:image_link"),
        })
    return out


def pid_from_link(link):
    """link == product_url(pid) == SITE + '/urun/' + pid + '/'  (pid'de escaping yok)."""
    prefix = build.SITE + "/urun/"
    assert link.startswith(prefix) and link.endswith("/"), "beklenmedik link bicimi: " + repr(link)
    return link[len(prefix):-1]


def gen_and_parse(products):
    xml, n = build.render_merchant_feed(products)
    return xml, n, parse_items(xml)


def main():
    with open(build.JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)
    print("urunler.json: %d urun yuklendi (%s)" % (len(products), build.JSON_PATH))

    # feed'e girmesi GEREKEN urunler (bagimsiz filtre; render_merchant_feed ile ayni kural) ----
    eligible = []
    for p in products:
        if p.get("parametrik"):
            continue
        if not build.feed_price((p.get("fiyat") or "").strip()):
            continue
        if not build.images_of(p):
            continue
        eligible.append(p)
    expected_n = len(eligible)
    by_pid = {p["id"]: p for p in eligible}
    print("feed'e uygun (parametrik degil + net fiyat + gorsel): %d urun" % expected_n)

    # ------------------------------------------------------------------ ONCE-KIRMIZI kaniti
    print("\n[RED PROOF] feed_id gecici NO-OP (eski davranis: g:id = pid) ile uret:")
    _orig = build.feed_id
    build.feed_id = lambda pid: pid
    try:
        _rxml, _rn, red_items = gen_and_parse(products)
    finally:
        build.feed_id = _orig
    red_over = [it for it in red_items if it["id"] is not None and len(it["id"]) > 50]
    check("eski davranista g:id > 50 karakter VAR (kirmizi kanit)",
          len(red_over) > 0,
          "%d adet g:id > 50 (bu duzeltilmezse Google reddeder)" % len(red_over))

    # ------------------------------------------------------------------ GERCEK (yesil) uretim
    print("\n[GREEN] gercek feed_id ile uret + dogrula:")
    xml, n, items = gen_and_parse(products)

    # (e) item sayisi korunmus
    check("(e) feed item sayisi = uygun urun sayisi",
          n == expected_n and len(items) == expected_n,
          "feed_n=%d, parse=%d, beklenen=%d" % (n, len(items), expected_n))

    # (a) hicbir g:id > 50 degil
    over = [it for it in items if it["id"] is None or len(it["id"]) > 50]
    check("(a) hicbir g:id > 50 karakter degil",
          len(over) == 0,
          "kirmizidan (%d) -> 0'a indi" % len(red_over) if not over
          else "%d adet hala >50" % len(over))

    # (b) tum g:id'ler global benzersiz
    ids = [it["id"] for it in items]
    dups = sorted(set(x for x in ids if ids.count(x) > 1)) if len(ids) != len(set(ids)) else []
    check("(b) tum g:id'ler benzersiz (kisa + donusturulmus global)",
          len(ids) == len(set(ids)),
          "%d id, %d benzersiz%s" % (len(ids), len(set(ids)),
                                     "" if not dups else "; cakisan: " + ", ".join(dups[:3])))

    # (c) kisa id'li urunlerde g:id/g:mpn = pid (korundu);  uzun id'de = feed_id(pid)
    kept_short = 0
    converted = 0
    c_ok = True
    d_ok = True
    example = None
    for it in items:
        pid = pid_from_link(it["link"])
        exp_fid = build.feed_id(pid)
        # (c)
        if it["id"] != exp_fid or it["mpn"] != exp_fid:
            c_ok = False
        if len(pid) <= 50:
            if it["id"] == pid and it["mpn"] == pid:
                kept_short += 1
            else:
                c_ok = False
        else:
            converted += 1
            if len(it["id"]) != 50:
                c_ok = False
            if example is None:
                example = (pid, it["id"])
        # (d) link TAM pid iceriyor + image_link kaynak gorselle ayni (degismedi)
        prod = by_pid.get(pid)
        if prod is None or pid not in it["link"] or it["link"] != build.product_url(pid):
            d_ok = False
        if prod is not None:
            exp_img = build.esc(build.images_of(prod)[0])
            if it["img"] != exp_img:
                d_ok = False

    check("(c) kisa id'ler pid ile birebir; uzun id'ler feed_id(pid) (g:id=g:mpn)",
          c_ok,
          "korunan kisa=%d, donusturulen uzun=%d" % (kept_short, converted))
    check("(d) <link> TAM pid iceriyor + <g:image_link> kaynak gorselle ayni (URL degismedi)",
          d_ok,
          "link=product_url(pid), image_link=gorseller[0] (degismedi)")

    if example:
        print("\n  ornek donusum (uzun pid -> 50'lik feed_id):")
        print("    pid      (%2d): %s" % (len(example[0]), example[0]))
        print("    feed_id  (%2d): %s" % (len(example[1]), example[1]))

    # ------------------------------------------------------------------ feed_id birim testleri
    print("\n[UNIT] feed_id():")
    p50 = "a" * 50
    p51 = "b" * 51
    plong = "otomobil-audi-a4-b8-on-tampon-braketi-sag-taraf-2008-2015-model-uyumlu-xyz"
    fid_long = build.feed_id(plong)
    check("tam 50 karakter -> AYNEN (korundu)", build.feed_id(p50) == p50,
          "len=%d" % len(build.feed_id(p50)))
    check("51 karakter -> 50 karaktere iner", len(build.feed_id(p51)) == 50,
          "%d -> %d" % (len(p51), len(build.feed_id(p51))))
    check("uzun pid -> feed_id TAM 50 karakter", len(fid_long) == 50,
          "len=%d" % len(fid_long))
    check("uzun pid -> feed_id = pid[:41] + '-' + sha1[:8] (deterministik/kalici)",
          fid_long == plong[:41] + "-" + __import__("hashlib").sha1(plong.encode("utf-8")).hexdigest()[:8]
          and fid_long[41] == "-" and re.fullmatch(r"[0-9a-f]{8}", fid_long[42:]) is not None,
          fid_long)
    check("ayni uzun pid -> ayni cikti (deterministik)",
          build.feed_id(plong) == build.feed_id(plong))
    check("kisa pid -> AYNEN (churn yok)", build.feed_id("audi-a4-braket") == "audi-a4-braket")

    # ------------------------------------------------------------------ sonuc
    print("\n" + ("=" * 60))
    if FAILS:
        print("SONUC: KIRMIZI — %d kontrol basarisiz: %s" % (len(FAILS), "; ".join(FAILS)))
        return 1
    print("SONUC: YESIL — tum kontroller gecti "
          "(kirmizi %d g:id>50 -> 0; korunan kisa=%d; donusturulen=%d; %d benzersiz)"
          % (len(red_over), kept_short, converted, len(set(ids))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
