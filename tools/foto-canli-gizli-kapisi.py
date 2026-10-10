#!/usr/bin/env python3
"""FOTO CANLI GIZLI KAPISI — program kapaliyken foto bolumu (#fotoUretim) CANLIDA gorunmez (Okan 10 Eki).

Birim testi (shop/test/foto-uretim.mjs KG1-3) kaynagi olcer; bu kapi deploy SONRASI gercek pruvo3d.com'u olcer:
  1. Canli ana sayfa HTML'i (cache-bust'SIZ canonical https://pruvo3d.com/) + oradan yayindaki
     foto-uretim-veri.js / foto-uretim.js (sayfanin kendi `<script src>`'i, `?v=` dahil).
  2. Program durumu: bolum kodunun KENDI okudugu uc (foto-uretim.js `ACIK_URL`, kaynaktan okunur; D1 YOK).
  3. Program kapali (acik!==true ya da tur listesi bos) ise iki kol birlikte tutmali:
     (a) HTML'de #fotoUretim statik `hidden` tasir;
     (b) yayindaki foto-uretim.js bu `/acik` yanitiyla bolumu ACMAZ (tools/foto-canli-gizli-karar.mjs, sahte
         DOM + vm, KG1-3 yolu) — ve ayni kosucu pozitif kontrolde ("acik + 1 tur") bolumu ACAR (kor degil).

Cikis:
  FOTO_CANLI_GIZLI=YESIL acik_tur=0 ...         rc 0
  FOTO_CANLI_GIZLI=UYGULANMAZ acik_tur=<n>      rc 0  (program acik: bolumun gorunmesi DOGRU)
  FOTO_CANLI_GIZLI=KIRMIZI sebep=<...>          rc 1  (+ geri alma komutu; otomatik rollback YOK)
  FOTO_CANLI_GIZLI=OLCULEMEDI sebep=<...>       rc 2  (ag hatasi / kosucu kor — YESIL DEGIL)
OLCULEMEDI'de --deneme kez (varsayilan 3) --bekle sn arayla yeniden denenir; tavan dolunca rc 2.

Agsiz test: --fikstur-html <dosya> --fikstur-acik <dosya> [--fikstur-js <dosya> --fikstur-veri <dosya>]
(js/veri verilmezse depodaki foto-uretim.js / foto-uretim-veri.js). --fikstur-acik-ok 0: /acik HTTP hatasi taklidi.
Kabul: tools/foto-canli-gizli-kapisi-test.py.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DEPO = BURASI.parent
KARAR = BURASI / "foto-canli-gizli-karar.mjs"
KOK_URL = "https://pruvo3d.com/"
BOLUM_ID = "fotoUretim"
UA = "pruvo-foto-canli-gizli-kapisi/1"
ZAMAN_ASIMI = 20

GERI_AL = (
    "GERI_AL (otomatik DEGIL; onceki Pages dagitimini yeniden yayinla):\n"
    "  gh run list --workflow deploy.yml --branch main --status success --limit 2 --json databaseId,headSha\n"
    "  gh run rerun <bir-onceki-basarili-databaseId>\n"
    "  (ya da bozan commit'i geri al: git revert <sha> && git push origin main)"
)


class Olculemedi(Exception):
    pass


class _BolumBul(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bolum = None  # None = yok; aksi halde ozellik sozlugu
        self.betikler = []

    def handle_starttag(self, etiket, ozellikler):
        o = dict(ozellikler)
        if o.get("id") == BOLUM_ID and self.bolum is None:
            self.bolum = o
        if etiket == "script" and o.get("src"):
            self.betikler.append(o["src"])


def html_coz(html):
    p = _BolumBul()
    p.feed(html)
    return p.bolum, p.betikler


def getir(url):
    """(ok, durum, govde_metni). Ag hatasi (yanit yok) -> Olculemedi; HTTP hata kodu YANIT sayilir."""
    istek = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as r:
            return True, r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            govde = e.read().decode("utf-8", "replace")
        except Exception:
            govde = ""
        return False, e.code, govde
    except Exception as e:  # DNS / baglanti / zaman asimi
        raise Olculemedi("ag:%s" % type(e).__name__)


def betik_bul(betikler, ad):
    for s in betikler:
        yol = urllib.parse.urlsplit(s).path
        if yol.rsplit("/", 1)[-1] == ad:
            return s
    return None


def karar_kos(veri_yol, js_yol, acik_yol=None, ok=True, durum=200, pozitif=False):
    komut = ["node", str(KARAR), "--veri", str(veri_yol), "--js", str(js_yol)]
    if pozitif:
        komut.append("--pozitif")
    else:
        komut += ["--acik", str(acik_yol), "--ok", "1" if ok else "0", "--durum", str(durum)]
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Olculemedi("karar-kosucusu:%s" % type(e).__name__)
    try:
        sonuc = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        raise Olculemedi("karar-kosucusu-cikti rc=%s" % r.returncode)
    if r.returncode != 0 or sonuc.get("hata") or not isinstance(sonuc.get("gorunur"), bool):
        raise Olculemedi("karar-kosucusu:%s" % (sonuc.get("hata") or r.returncode))
    return sonuc["gorunur"]


def acik_turu(ok, veri):
    """Bolum kodunun acma sarti (foto-uretim.js acikYukle): ok + acik===true + tur listesi dolu."""
    if not ok or not isinstance(veri, dict) or veri.get("acik") is not True:
        return 0
    turler = veri.get("turler")
    return len(turler) if isinstance(turler, list) else 0


def olc(a, gecici):
    """Tek olcum. Donus: (hukum, ayrinti). Olculemedi firlatabilir."""
    if a.fikstur_html:
        html = Path(a.fikstur_html).read_text(encoding="utf-8")
        acik_metin = Path(a.fikstur_acik).read_text(encoding="utf-8")
        acik_ok, acik_durum = a.fikstur_acik_ok != "0", 200 if a.fikstur_acik_ok != "0" else 503
        js_yol = Path(a.fikstur_js) if a.fikstur_js else DEPO / "foto-uretim.js"
        veri_yol = Path(a.fikstur_veri) if a.fikstur_veri else DEPO / "foto-uretim-veri.js"
        bolum, _ = html_coz(html)
        js_metin = js_yol.read_text(encoding="utf-8")
    else:
        ok, durum, html = getir(a.kok)
        if not ok:
            raise Olculemedi("ana-sayfa-http-%s" % durum)
        bolum, betikler = html_coz(html)
        js_src, veri_src = betik_bul(betikler, "foto-uretim.js"), betik_bul(betikler, "foto-uretim-veri.js")
        if not js_src or not veri_src:
            raise Olculemedi("betik-yok js=%s veri=%s" % (bool(js_src), bool(veri_src)))
        ok_j, d_j, js_metin = getir(urllib.parse.urljoin(a.kok, js_src))
        ok_v, d_v, veri_metin = getir(urllib.parse.urljoin(a.kok, veri_src))
        if not ok_j or not ok_v:
            raise Olculemedi("betik-http js=%s veri=%s" % (d_j, d_v))
        js_yol, veri_yol = Path(gecici) / "foto-uretim.js", Path(gecici) / "foto-uretim-veri.js"
        js_yol.write_text(js_metin, encoding="utf-8")
        veri_yol.write_text(veri_metin, encoding="utf-8")
        # Program durumu: bolum kodunun KENDI okudugu uc (ACIK_URL) — ikinci bir uc tahmin edilmez.
        m = re.search(r'var\s+ACIK_URL\s*=\s*"([^"]+)"', js_metin)
        if not m:
            raise Olculemedi("acik-url-yok")
        acik_ok, acik_durum, acik_metin = getir(urllib.parse.urljoin(a.kok, m.group(1)))

    try:
        acik_veri = json.loads(acik_metin)
    except Exception:
        acik_veri = None
    n = acik_turu(acik_ok, acik_veri)
    if n > 0:
        return "UYGULANMAZ", "acik_tur=%d" % n
    acik_yol = Path(gecici) / "acik.json"
    acik_yol.write_text(acik_metin if acik_veri is not None else "", encoding="utf-8")

    if bolum is None:
        return "KIRMIZI", "sebep=bolum-yok (#%s HTML'de bulunamadi; kapi kor kalmasin diye fail-closed)" % BOLUM_ID
    html_gizli = "hidden" in bolum
    js_gorunur = karar_kos(veri_yol, js_yol, acik_yol, acik_ok, acik_durum)
    # Pozitif kontrol: ayni kosucu "acik + 1 tur" ile bolumu ACAMIYORSA (b) kolu kordur -> YESIL verilmez.
    if not karar_kos(veri_yol, js_yol, pozitif=True):
        raise Olculemedi("pozitif-kontrol (kosucu acik programda bile bolumu acamadi: karar kolu kor)")
    sebepler = []
    if not html_gizli:  # MUTANT-CAPA-A
        sebepler.append("html-hidden-yok")
    if js_gorunur:  # MUTANT-CAPA-B
        sebepler.append("js-aciyor")
    ozet = "acik_tur=0 html_hidden=%d js_gorunur=%d pozitif=1" % (html_gizli, js_gorunur)
    if sebepler:
        return "KIRMIZI", "sebep=%s %s" % ("+".join(sebepler), ozet)
    return "YESIL", ozet


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kok", default=KOK_URL)
    p.add_argument("--fikstur-html")
    p.add_argument("--fikstur-acik")
    p.add_argument("--fikstur-acik-ok", default="1")
    p.add_argument("--fikstur-js")
    p.add_argument("--fikstur-veri")
    p.add_argument("--deneme", type=int, default=3)
    p.add_argument("--bekle", type=float, default=10.0)
    a = p.parse_args()
    if bool(a.fikstur_html) != bool(a.fikstur_acik):
        print("FOTO_CANLI_GIZLI=OLCULEMEDI sebep=arguman (--fikstur-html ve --fikstur-acik birlikte verilir)")
        return 2

    sebep = "?"
    for deneme in range(1, max(1, a.deneme) + 1):
        with tempfile.TemporaryDirectory(prefix="foto-canli-gizli-") as gecici:
            try:
                hukum, ayrinti = olc(a, gecici)
            except Olculemedi as e:
                sebep = str(e)
                print("deneme %d/%d OLCULEMEDI: %s" % (deneme, a.deneme, sebep), file=sys.stderr)
                if deneme < a.deneme:
                    time.sleep(a.bekle)
                continue
        print("FOTO_CANLI_GIZLI=%s %s" % (hukum, ayrinti))
        if hukum == "KIRMIZI":
            print(GERI_AL)
            return 1
        return 0
    print("FOTO_CANLI_GIZLI=OLCULEMEDI sebep=%s deneme=%d (YESIL DEGIL)" % (sebep, a.deneme))
    return 2


if __name__ == "__main__":
    sys.exit(main())
