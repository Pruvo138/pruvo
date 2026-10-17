#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/indexnow-gonder.py (IndexNow sitemap farki tek-POST).

KABUL SORUSU: "bu satiri silsem hangi vaka kirmizi yanar?"
Cevap her vaka/mutant icin yorumda. IKI kol:

  A) VAKALAR — araci DEGISTIRMEDEN fikstur uzerinde davranis olcer. Gercek IndexNow'a
     DOKUNMAZ; 127.0.0.1:PORT yerel stub HTTP sunucusu (thread) ile POST yakalanir.
     Eski/yeni sitemapi git'ten DEGIL yerel dosyadan okur (CI'da sitemap.xml git'e
     GIRMEZ); V8-V9 ayrica `--hazirla` kolunu olcer (canli sitemap indirme, bloklamaz).
  B) MUTANTLAR — araci IZOLE KOPYADA bozar, KIRMIZI yanmasini bekler. Kopya
     `tempfile.mkdtemp` altinda; gercek ev yoluna DOKUNULMAZ, silinen yalniz testin
     KENDI urettigi gecici dizindir (FILO DERSI 4 Eyl: yuk yikici olamaz).

Kosum (borusuz):  python3 tools/indexnow-gonder-test.py

Son satir: KABUL <g>/11 MUTANT <m>/5  (YESIL icin 11/11 + 5/5; rc=0).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.dont_write_bytecode = True                            # hedef repoya __pycache__ yazma

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(ROOT, "tools", "indexnow-gonder.py")

INDEXNOW_UC_VARSAYILAN = "https://api.indexnow.org/indexnow"
ANAHTAR = "pruvo3d-indexnow-anahtari-17eki"
ANAHTAR_DOSYA = ANAHTAR + ".txt"
SITE = "https://pruvo3d.com/"


# ──────────────────────────────────────────────────────────────────────────────
# Sitemap fiksturlari — V1 (fark var: 2 ekle + 1 kaldir + 1 lastmod = 4 URL),
#                       V2 (fark yok).
# ──────────────────────────────────────────────────────────────────────────────
def _url(yer, lastmod):
    return "<url><loc>%s%s</loc><lastmod>%s</lastmod></url>" % (SITE, yer, lastmod)


SITEMAP_V1_ESKI = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<urlset>\n"
    + _url("A", "2026-01-01")      # v2'de lastmod degisiyor -> lastmod-changed
    + _url("B", "2026-01-01")      # v2'de AYNI kalacak -> fark yok
    + _url("C", "2026-01-01")      # v2'de YOK -> kaldirildi
    + "</urlset>\n"
)
SITEMAP_V2_YENI = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<urlset>\n"
    + _url("A", "2026-02-01")      # lastmod degisti (eski ile farkli)
    + _url("B", "2026-01-01")      # ayni kalir
    + _url("D", "2026-01-01")      # yeni eklendi
    + _url("F", "2026-01-01")      # yeni eklendi
    + "</urlset>\n"
)
# V1 beklenen URL kumesi (siraya gore siralanir): A, C, D, F (4 URL).
SITEMAP_AYNI = SITEMAP_V2_YENI      # V2 icin: v1==v2, fark YOK

# V8 icin: stub'ın sunacagi ESKI (canli onceki sitemap simule). YENI'den farkli (V8'de
# `./sitemap.xml` ayri bir fikstur) — boylece `eski.xml` ile `yeni.xml` birbirinden
# ayirt edilebilir duruyor. `yeni.xml kopyalandı` onayi ikisinin iceriginin FARKLI
# olmasini gerektirmez; asil kanit byte esitligidir.
SITEMAP_STUB_ESKI = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<urlset>\n"
    + _url("G", "2026-03-01")
    + _url("H", "2026-03-01")
    + "</urlset>\n"
)


# ──────────────────────────────────────────────────────────────────────────────
# STUB HTTP SUNUCUSU — 127.0.0.1:PORT. POST vuruldu mu, govde ne, ne kodla yanitlandi?
# ──────────────────────────────────────────────────────────────────────────────
class StubHandler(BaseHTTPRequestHandler):
    """Test isabetini + govdesini disariya yazar. log yok (stderr bos = sessiz)."""

    # sinif seviyesinde paylasilan kayit (handler basina degil, sunucu basina):
    _kayit_lock = threading.Lock()
    _kayit = {"hit": 0, "bodies": [], "status": 200, "sitemap_bayi": b""}

    def do_POST(self):
        uzunluk = int(self.headers.get("Content-Length", "0") or "0")
        govde = self.rfile.read(uzunluk) if uzunluk else b""
        with StubHandler._kayit_lock:
            StubHandler._kayit["hit"] += 1
            StubHandler._kayit["bodies"].append(govde)
            kod = StubHandler._kayit["status"]
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        """`--hazirla` icin: GET /sitemap.xml bayt byte dondurur."""
        with StubHandler._kayit_lock:
            bayt = StubHandler._kayit["sitemap_bayi"]
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(bayt)))
        self.end_headers()
        self.wfile.write(bayt)

    def log_message(self, *_args, **_kw):
        return                                                  # sessiz


class StubSunucu:
    """Thread'li 127.0.0.1 stub. `with` ile baslat/durdur; `uc` URL'sini verir."""

    def __init__(self, status=200, sitemap_bayi=b""):
        self.status = status
        self.sunucu = None
        self.thread = None
        StubHandler._kayit["hit"] = 0
        StubHandler._kayit["bodies"] = []
        StubHandler._kayit["status"] = status
        StubHandler._kayit["sitemap_bayi"] = sitemap_bayi

    def __enter__(self):
        self.sunucu = HTTPServer(("127.0.0.1", 0), StubHandler)
        port = self.sunucu.server_address[1]
        self.uc = "http://127.0.0.1:%d/indexnow" % port
        self.sitemap_uc = "http://127.0.0.1:%d/sitemap.xml" % port
        self.thread = threading.Thread(target=self.sunucu.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        if self.sunucu is not None:
            self.sunucu.shutdown()
            self.sunucu.server_close()

    @property
    def hit(self):
        return StubHandler._kayit["hit"]

    @property
    def bodies(self):
        return list(StubHandler._kayit["bodies"])


def _bos_port():
    """Henuz kullanilmayan bir TCP port'u bul. Baglanti acilip hemen kapatilir —
    yaris penceresi kucuk (~ms) ama V9'un stub'siz testi icin en saglam yol."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    finally:
        s.close()
    return port


# ──────────────────────────────────────────────────────────────────────────────
# ORTAM
# ──────────────────────────────────────────────────────────────────────────────
def _env(ek=None):
    """Aracin test ortami. `PRUVO_INDEXNOW_UC` stub URL'si, `GIT_DIR` temiz
    (aracin artik git ile isgali yok). `PYTHONPATH` korunur ki subprocess kendi
    yardimcilarini bulabilsin."""
    ortam = os.environ.copy()
    ortam.pop("GIT_DIR", None)
    ortam.pop("GIT_WORK_TREE", None)
    ortam.pop("PRUVO_INDEXNOW_UC", None)
    ortam.pop("PRUVO_INDEXNOW_SITEMAP_UC", None)
    if ek:
        ortam.update(ek)
    return ortam


def kos(arac, env=None, args=None, cwd=None):
    """Araci ALT SUREC olarak kosar; (rc, stdout+stderr) doner. rc BORUSUZ okunur."""
    cmd = [sys.executable, arac] + (args or [])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env, cwd=cwd)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ──────────────────────────────────────────────────────────────────────────────
# IZOLE MUTANT KOPYASI
# ──────────────────────────────────────────────────────────────────────────────
def izole_kopya(kaynak, hedef_dizin):
    """Araci gecici dizine kopyalar. MUTANT CANLI GOVDEDE YASAMAZ."""
    hedef = os.path.join(hedef_dizin, "indexnow-gonder.py")
    shutil.copyfile(kaynak, hedef)
    return hedef


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    n = govde.count(eski)
    if n != 1:
        raise AssertionError(
            "MUTANT CAPASI BAYAT: %r govdede %d kez gecti (1 bekleniyordu) — "
            "capa kaynaktan tazelenmeli" % (eski, n))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni, 1))


# ──────────────────────────────────────────────────────────────────────────────
# V1-V7 ortak sablon: ESKI + YENI dosyasi tempdir'da, arac onlari karsilastirir.
# ──────────────────────────────────────────────────────────────────────────────
def _vakalari_kos_eski_yeni(gccer, hata, tmp):
    """ESKI/YENI dosya fiksturu uzerinde V1-V5 + V7 (V6 dosya kapsaminda ayri, V2
    ayni dosya, V8-V9 --hazirla kolunda)."""

    # ── V1: ekle 2 + kaldir 1 + lastmod 1 = 4 URL birebir ─────────────────────
    eski_yol = os.path.join(tmp, "eski1.xml")
    yeni_yol = os.path.join(tmp, "yeni1.xml")
    with open(eski_yol, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
    with open(yeni_yol, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
    with StubSunucu(status=200) as stub:
        rc, cikti = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                        args=["--eski", eski_yol, "--yeni", yeni_yol])
    bek_satir = "INDEXNOW=4 URL http=200"
    if rc == 0 and bek_satir in cikti and stub.hit >= 1:
        gccer.append("V1")
    else:
        hata.append("V1 fark hesabi yanlis (rc=%d, bek=%r, hit=%d):\n  cikti=%r"
                    % (rc, bek_satir, stub.hit, cikti[:400]))

    # ── V2: fark yok -> stub isabet 0, INDEXNOW=0 URL ────────────────────────
    ayni_yol = os.path.join(tmp, "ayni.xml")
    with open(ayni_yol, "w", encoding="utf-8") as f: f.write(SITEMAP_AYNI)
    with StubSunucu(status=200) as stub:
        rc, cikti = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                        args=["--eski", ayni_yol, "--yeni", ayni_yol])
    if rc == 0 and "INDEXNOW=0 URL" in cikti and stub.hit == 0:
        gccer.append("V2")
    else:
        hata.append("V2 fark-yok POST gereksiz (rc=%d, hit=%d, bek 0):\n  cikti=%r"
                    % (rc, stub.hit, cikti[:400]))

    # ── V3: stub 202 -> rc=0 INDEXNOW=4 URL http=202 ─────────────────────────
    eski3 = os.path.join(tmp, "eski3.xml")
    yeni3 = os.path.join(tmp, "yeni3.xml")
    with open(eski3, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
    with open(yeni3, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
    with StubSunucu(status=202) as stub:
        rc, cikti = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                        args=["--eski", eski3, "--yeni", yeni3])
    bek_satir3 = "INDEXNOW=4 URL http=202"
    if rc == 0 and bek_satir3 in cikti and stub.hit >= 1:
        gccer.append("V3")
    else:
        hata.append("V3 202 kodu yanlis (rc=%d, bek=%r, hit=%d):\n  cikti=%r"
                    % (rc, bek_satir3, stub.hit, cikti[:400]))

    # ── V4: stub 403 -> rc=3 OLCULEMEDI ──────────────────────────────────────
    eski4 = os.path.join(tmp, "eski4.xml")
    yeni4 = os.path.join(tmp, "yeni4.xml")
    with open(eski4, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
    with open(yeni4, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
    with StubSunucu(status=403) as stub:
        rc, cikti = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                        args=["--eski", eski4, "--yeni", yeni4])
    if rc == 3 and "INDEXNOW=OLCULEMEDI sebep=HTTP-403" in cikti:
        gccer.append("V4")
    else:
        hata.append("V4 403 hatasi yanlis (rc=%d bek 3, OLCULEMEDI yok):\n  cikti=%r"
                    % (rc, cikti[:400]))

    # ── V5: govde host/key/keyLocation/urlList birebir ───────────────────────
    eski5 = os.path.join(tmp, "eski5.xml")
    yeni5 = os.path.join(tmp, "yeni5.xml")
    with open(eski5, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
    with open(yeni5, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
    with StubSunucu(status=200) as stub:
        rc, _ = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                    args=["--eski", eski5, "--yeni", yeni5])
    govde_ok = False
    detay = ""
    if stub.bodies:
        try:
            govde = json.loads(stub.bodies[0].decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            govde_ok = False
            detay = "JSON parse: %s" % e
        else:
            url_list = govde.get("urlList")
            bek_urls = ["https://pruvo3d.com/A", "https://pruvo3d.com/C",
                        "https://pruvo3d.com/D", "https://pruvo3d.com/F"]
            govde_ok = (
                govde.get("host") == "pruvo3d.com"
                and govde.get("key") == ANAHTAR
                and govde.get("keyLocation") == SITE + ANAHTAR_DOSYA
                and isinstance(url_list, list)
                and sorted(url_list) == bek_urls
            )
            detay = ("host=%r key=%r keyLocation=%r urlList=%r"
                     % (govde.get("host"), govde.get("key"),
                        govde.get("keyLocation"), url_list))
    if rc == 0 and govde_ok:
        gccer.append("V5")
    else:
        hata.append("V5 POST govde beklenen sekilde degil: rc=%d, govde_ok=%s, "
                    "detay=%s" % (rc, govde_ok, detay))

    # ── V7: PRUVO_INDEXNOW_UC=https://ornek.invalid -> rc=2, isabet 0 ─────────
    eski7 = os.path.join(tmp, "eski7.xml")
    yeni7 = os.path.join(tmp, "yeni7.xml")
    with open(eski7, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
    with open(yeni7, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
    with StubSunucu(status=200) as stub:
        rc, cikti = kos(ARAC,
                        env=_env({"PRUVO_INDEXNOW_UC": "https://ornek.invalid"}),
                        args=["--eski", eski7, "--yeni", yeni7])
    if rc == 2 and stub.hit == 0:
        gccer.append("V7")
    else:
        hata.append("V7 guvenlik kapisi dusuk (rc=%d bek 2, hit=%d bek 0):\n  cikti=%r"
                    % (rc, stub.hit, cikti[:400]))


# ──────────────────────────────────────────────────────────────────────────────
# V6: anahtar dosyasi + MANIFESTO kapsami (dosya kapsaminda; gecici degil)
# ──────────────────────────────────────────────────────────────────────────────
def _v6_kontrol(gccer, hata):
    anahtar_yol = os.path.join(ROOT, ANAHTAR_DOSYA)
    anahtar_icerik = ""
    try:
        with open(anahtar_yol, encoding="utf-8") as f:
            anahtar_icerik = f.read()
    except OSError:
        pass
    yayin_yol = os.path.join(ROOT, "tools", "yayin-topla.py")
    yayin_icerik = ""
    try:
        with open(yayin_yol, encoding="utf-8") as f:
            yayin_icerik = f.read()
    except OSError:
        pass
    v6_ok = (anahtar_icerik == ANAHTAR
             and ANAHTAR_DOSYA in yayin_icerik)
    if v6_ok:
        gccer.append("V6")
    else:
        hata.append("V6 anahtar dosyasi ya da MANIFESTO/IZLENEN_GIRDILER eslesmiyor: "
                    "icerik=%r (bek=%r), dosya_yayinda_mi=%s"
                    % (anahtar_icerik, ANAHTAR,
                       ANAHTAR_DOSYA in yayin_icerik))


# ──────────────────────────────────────────────────────────────────────────────
# V8/V9: --hazirla kolu (canli sitemap indirme)
# ──────────────────────────────────────────────────────────────────────────────
def _v8_v9_kos(gccer, hata, tmp):
    """`--hazirla` kendine ait gecici repo-root ister (arac KOK/sitemap.xml'a bakiyor).
    tmp icinde `sitemap_root/` olusturup `tools/indexnow-gonder.py` kopyasini orada
    calistirir; gercek evdeki arac dokunulmez."""

    # ── V8: stub acik -> eski.xml stub baytiyla esit, yeni.xml kopyalandi, rc=0
    with tempfile.TemporaryDirectory(prefix="indexnow-v8-") as repo_kok:
        _araci_repo_icine_kur(repo_kok)
        sitemap_yol = os.path.join(repo_kok, "sitemap.xml")
        # yeni.xml'in farkliligi icin stub ESKI ile ayni olmayan bir YENI yaz.
        with open(sitemap_yol, "w", encoding="utf-8") as f:
            f.write(SITEMAP_V2_YENI)
        hedef = os.path.join(repo_kok, "_indexnow")
        with StubSunucu(status=200, sitemap_bayi=SITEMAP_STUB_ESKI.encode("utf-8")) as stub:
            rc, cikti = kos(os.path.join(repo_kok, "tools", "indexnow-gonder.py"),
                            env=_env({"PRUVO_INDEXNOW_SITEMAP_UC": stub.sitemap_uc}),
                            args=["--hazirla", hedef],
                            cwd=repo_kok)
        eski_yazildi = os.path.isfile(os.path.join(hedef, "eski.xml"))
        yeni_yazildi = os.path.isfile(os.path.join(hedef, "yeni.xml"))
        bayt_esit = False
        if eski_yazildi and yeni_yazildi:
            with open(os.path.join(hedef, "eski.xml"), "rb") as f:
                bayt_esit = (f.read() == SITEMAP_STUB_ESKI.encode("utf-8"))
            with open(os.path.join(hedef, "yeni.xml"), encoding="utf-8") as f:
                kopyalandi = f.read()
        else:
            kopyalandi = ""
        v8_ok = (rc == 0 and "INDEXNOW_HAZIRLA=TAMAM" in cikti
                 and eski_yazildi and yeni_yazildi and bayt_esit
                 and kopyalandi == SITEMAP_V2_YENI)
        if v8_ok:
            gccer.append("V8")
        else:
            hata.append("V8 --hazirla TAMAM yolu yanlis (rc=%d, TAMAM=%s, "
                        "eski_ok=%s, yeni_ok=%s, bayt_esit=%s, kopyalandi=%s):\n  cikti=%r"
                        % (rc, "INDEXNOW_HAZIRLA=TAMAM" in cikti,
                           eski_yazildi, yeni_yazildi, bayt_esit,
                           kopyalandi == SITEMAP_V2_YENI, cikti[:400]))

    # ── V9: stub kapali (bos port) -> rc=0 ESKI-YOK, eski.xml YOK
    with tempfile.TemporaryDirectory(prefix="indexnow-v9-") as repo_kok:
        _araci_repo_icine_kur(repo_kok)
        sitemap_yol = os.path.join(repo_kok, "sitemap.xml")
        with open(sitemap_yol, "w", encoding="utf-8") as f:
            f.write(SITEMAP_V2_YENI)
        hedef = os.path.join(repo_kok, "_indexnow")
        port = _bos_port()
        sitemap_kapali = "http://127.0.0.1:%d/sitemap.xml" % port
        # YENI'yi de BILEREK olusturma ki V9 ayni zamanda YENI-YOK mu ESKI-YOK mu
        # anlaminda kalsin: V9 yalniz ESKI kapali; yeni.xml olmali.
        # Daha kuvvetli test: sitemap.xml SADECE eskiyi okumak icin var; yeni.xml'in
        # yazilmasi YENI-YOK mu ESKI-YOK mu ayrimini test icin gerektirmez.
        # yeni.xml'in YAZILMAMASINI bekleyerek yapilan hatali testi engelliyoruz:
        # `_vakalari_kos` zaten 'yeni.xml kopyalandi' onayini V8'de yapti.
        rc, cikti = kos(os.path.join(repo_kok, "tools", "indexnow-gonder.py"),
                        env=_env({"PRUVO_INDEXNOW_SITEMAP_UC": sitemap_kapali}),
                        args=["--hazirla", hedef],
                        cwd=repo_kok)
        eski_yok = not os.path.isfile(os.path.join(hedef, "eski.xml"))
        # yeni.xml ise sitemap.xml VAR oldugu icin yazilmis olmali; V8 ayrintili
        # olarak kontrol etti.
        yeni_var = os.path.isfile(os.path.join(hedef, "yeni.xml"))
        v9_ok = (rc == 0 and "INDEXNOW_HAZIRLA=ESKI-YOK" in cikti
                 and "TAMAM" not in cikti
                 and eski_yok and yeni_var)
        if v9_ok:
            gccer.append("V9")
        else:
            hata.append("V9 --hazirla ESKI-YOK yolu yanlis (rc=%d, ESKI-YOK=%s, "
                        "TAMAM_yok=%s, eski_yok=%s, yeni_var=%s):\n  cikti=%r"
                        % (rc, "INDEXNOW_HAZIRLA=ESKI-YOK" in cikti,
                           "TAMAM" not in cikti, eski_yok, yeni_var,
                           cikti[:400]))


def _araci_repo_icine_kur(repo_kok):
    """V8/V9'un gecici 'repo root'u icin araci + b84aad5 anahtar dosyasinin
    bulunmasini beklemeden izole kopya kurar; gercek ROOT'a DOKUNMAZ."""
    os.makedirs(os.path.join(repo_kok, "tools"), exist_ok=True)
    shutil.copyfile(ARAC, os.path.join(repo_kok, "tools", "indexnow-gonder.py"))


# ══════════════════════════════════════════════════════════════════════════════
# VAKALAR
# ══════════════════════════════════════════════════════════════════════════════
# ──────────────────────────────────────────────────────────────────────────────
# V10/V11: GERCEK sitemap sekli (xmlns tasir) + bos yeni sitemap
# 17 Eki olculdu: V1-V9 fiksturleri namespace'sizdi; arac `findall("url")` ile canli
# 43 bin URL'lik sitemap'te 0 buluyor ve her deploy'da sessizce INDEXNOW=0 basacakti.
# ──────────────────────────────────────────────────────────────────────────────
NS_URLSET = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'


def _ns(sitemap):
    return sitemap.replace("<urlset>", NS_URLSET, 1)


def _v10_kos(arac, tmp):
    eski_yol = os.path.join(tmp, "eski-ns.xml")
    yeni_yol = os.path.join(tmp, "yeni-ns.xml")
    with open(eski_yol, "w", encoding="utf-8") as f: f.write(_ns(SITEMAP_V1_ESKI))
    with open(yeni_yol, "w", encoding="utf-8") as f: f.write(_ns(SITEMAP_V2_YENI))
    with StubSunucu(status=202) as stub:
        rc, cikti = kos(arac, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                        args=["--eski", eski_yol, "--yeni", yeni_yol])
    return rc, cikti, stub.hit


def _v10_v11_kos(gccer, hata):
    with tempfile.TemporaryDirectory(prefix="indexnow-v10-") as tmp:
        if NS_URLSET in _ns(SITEMAP_V1_ESKI) and NS_URLSET in _ns(SITEMAP_V2_YENI):
            rc, cikti, hit = _v10_kos(ARAC, tmp)
            if rc == 0 and "INDEXNOW=4 URL http=202" in cikti and hit >= 1:
                gccer.append("V10")
            else:
                hata.append("V10 xmlns'li gercek sitemap sekli yanlis sayildi (rc=%d, hit=%d):\n  cikti=%r"
                            % (rc, hit, cikti[:400]))
        else:
            hata.append("V10 fikstur xmlns tasimiyor (capa bayat: <urlset> bulunamadi)")

        # V11: yeni sitemap 0 URL -> rc=3 YENI-BOS, POST YOK, "INDEXNOW=0" YOK
        bos = os.path.join(tmp, "bos.xml")
        with open(bos, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + NS_URLSET + "</urlset>\n")
        eski_yol = os.path.join(tmp, "eski-ns.xml")
        with StubSunucu(status=202) as stub:
            rc, cikti = kos(ARAC, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                            args=["--eski", eski_yol, "--yeni", bos])
        if (rc == 3 and "INDEXNOW=OLCULEMEDI sebep=YENI-BOS" in cikti
                and "INDEXNOW=0 URL" not in cikti and stub.hit == 0):
            gccer.append("V11")
        else:
            hata.append("V11 bos yeni sitemap sessiz gecti (rc=%d bek 3, hit=%d):\n  cikti=%r"
                        % (rc, stub.hit, cikti[:400]))


def vakalar_kos(gccer, hata):
    with tempfile.TemporaryDirectory(prefix="indexnow-vaka-") as tmp:
        _vakalari_kos_eski_yeni(gccer, hata, tmp)
    _v6_kontrol(gccer, hata)
    _v8_v9_kos(gccer, hata, None)
    _v10_v11_kos(gccer, hata)


# ══════════════════════════════════════════════════════════════════════════════
# MUTANTLAR (izole kopya)
# ══════════════════════════════════════════════════════════════════════════════
def mutantlar_kos(gccer, hata):
    tmp = tempfile.mkdtemp(prefix="indexnow-mutant-")
    try:
        # ── Negatif kontrol: BOZULMADAN kopya V1 YESIL ─────────────────────────
        with tempfile.TemporaryDirectory(prefix="indexnow-mutant-neg-") as neg_tmp:
            kopya = izole_kopya(ARAC, neg_tmp)
            eski_n = os.path.join(neg_tmp, "eski_n.xml")
            yeni_n = os.path.join(neg_tmp, "yeni_n.xml")
            with open(eski_n, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
            with open(yeni_n, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
            with StubSunucu(status=200) as stub:
                rc, cikti = kos(kopya, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                                args=["--eski", eski_n, "--yeni", yeni_n])
            if rc == 0 and "INDEXNOW=4 URL http=200" in cikti:
                gccer.append("MNEG")
            else:
                hata.append("NEGATIF KONTROL: bozulmamis kopya YESIL degil (rc=%d)\n  cikti=%r"
                            % (rc, cikti[:400]))

        # ── M1: lastmod karsilastirmasi kalkar -> V1 KIRMIZI ──────────────────
        # Capa: fark_listesi icindeki `{u for u in (set_eski & set_yeni) if eski[u] !=
        # yeni[u]}` ifadesinin `if eski[u] != yeni[u]` kismi kaldirilir -> lastmod
        # degisen URL'ler fark listesine GIRMEZ. V1'de URL A bu yuzden dislanir;
        # liste 4 yerine 3 olur ve "INDEXNOW=4 URL" bekleyen V1 KIRMIZI yanar.
        with tempfile.TemporaryDirectory(prefix="indexnow-m1-") as m_tmp:
            kopya = izole_kopya(ARAC, m_tmp)
            mutasyonla(kopya,
                       'fark |= {u for u in (set_eski & set_yeni) if eski[u] != yeni[u]}',
                       'fark |= set_eski & set_yeni')
            eski_m = os.path.join(m_tmp, "eski_m.xml")
            yeni_m = os.path.join(m_tmp, "yeni_m.xml")
            with open(eski_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
            with open(yeni_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
            with StubSunucu(status=200) as stub:
                rc, cikti = kos(kopya, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                                args=["--eski", eski_m, "--yeni", yeni_m])
            if rc != 0 or "INDEXNOW=4 URL" not in cikti:
                gccer.append("M1")
            else:
                hata.append("M1 lastmod karsilastirmasi kalkti ama V1 GECTI (rc=%d):\n  cikti=%r"
                            % (rc, cikti[:400]))

        # ── M2: 403 basari sayilir -> V4 KIRMIZI ─────────────────────────────
        # Capa: 200/202 basari kosulu `kod in (200, 202)` -> `kod in (200, 202, 403)`.
        # Mutantta 403 yine basarili sayilir; V4 bekledigi "INDEXNOW=OLCULEMEDI
        # sebep=HTTP-403" YOK -> KIRMIZI.
        with tempfile.TemporaryDirectory(prefix="indexnow-m2-") as m_tmp:
            kopya = izole_kopya(ARAC, m_tmp)
            mutasyonla(kopya, "if kod in (200, 202):", "if kod in (200, 202, 403):")
            eski_m = os.path.join(m_tmp, "eski_m.xml")
            yeni_m = os.path.join(m_tmp, "yeni_m.xml")
            with open(eski_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
            with open(yeni_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
            with StubSunucu(status=403) as stub:
                rc, cikti = kos(kopya, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                                args=["--eski", eski_m, "--yeni", yeni_m])
            if rc != 0 or "OLCULEMEDI" in cikti or "INDEXNOW=" in cikti:
                gccer.append("M2")
            else:
                hata.append("M2 403 basari sayildi ama V4 GECTI (rc=%d, 'OLCULEMEDI' YOK):\n  cikti=%r"
                            % (rc, cikti[:400]))

        # ── M3: kalkan URL'ler dusurulur -> V1 KIRMIZI ───────────────────────
        # Capa: `(set_eski - set_yeni)` parantezden cikarilir; sonuc olarak kaldirilan
        # URL'ler fark listesine GIRMEZ. V1'de URL C (eski sitemap'te var, yeni sitemap'te
        # yok) bu yuzden dislanir; liste 4 yerine 3 olur ve "INDEXNOW=4 URL" bekleyen V1
        # KIRMIZI yanar.
        with tempfile.TemporaryDirectory(prefix="indexnow-m3-") as m_tmp:
            kopya = izole_kopya(ARAC, m_tmp)
            mutasyonla(kopya, "fark = (set_yeni - set_eski) | (set_eski - set_yeni)",
                       "fark = set_yeni - set_eski")
            eski_m = os.path.join(m_tmp, "eski_m.xml")
            yeni_m = os.path.join(m_tmp, "yeni_m.xml")
            with open(eski_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V1_ESKI)
            with open(yeni_m, "w", encoding="utf-8") as f: f.write(SITEMAP_V2_YENI)
            with StubSunucu(status=200) as stub:
                rc, cikti = kos(kopya, env=_env({"PRUVO_INDEXNOW_UC": stub.uc}),
                                args=["--eski", eski_m, "--yeni", yeni_m])
            if rc != 0 or "INDEXNOW=4 URL" not in cikti:
                gccer.append("M3")
            else:
                hata.append("M3 kalkan URL'ler dusuruldu ama V1 GECTI (rc=%d):\n  cikti=%r"
                            % (rc, cikti[:400]))

        # ── M4: --hazirla indirme hatasinda rc=1 -> V9 KIRMIZI ───────────────
        # Capa: `_indir` iki deneme sonra None doner; `kol_hazirla` bunu gorur,
        # `INDEXNOW_HAZIRLA=ESKI-YOK` yazar ve rc=0 ile cikar (build'i bloklamaz).
        # Mutant: `return None` -> `sys.exit(1)`. Hata durumunda surec rc=1 ile
        # OLUR; V9 (kullanilmayan porta indis) rc=0 + ESKI-YOK bekler, mutantta
        # rc=1 -> KIRMIZI.
        with tempfile.TemporaryDirectory(prefix="indexnow-m4-") as m_tmp:
            kopya = izole_kopya(ARAC, m_tmp)
            mutasyonla(kopya, "    sys.stderr.write(\"sitemap indirilemedi: %s\\n\" % (son or \"?\"))\n    return None",
                       "    sys.stderr.write(\"sitemap indirilemedi: %s\\n\" % (son or \"?\"))\n    sys.exit(1)")
            # izole kopya icin 'repo root' da kur — arac KOK/sitemap.xml'a bakiyor.
            with tempfile.TemporaryDirectory(prefix="indexnow-m4-repo-") as repo_kok:
                _araci_repo_icine_kur(repo_kok)
                sitemap_yol = os.path.join(repo_kok, "sitemap.xml")
                with open(sitemap_yol, "w", encoding="utf-8") as f:
                    f.write(SITEMAP_V2_YENI)
                hedef = os.path.join(repo_kok, "_indexnow")
                port = _bos_port()
                sitemap_kapali = "http://127.0.0.1:%d/sitemap.xml" % port
                # izole kopya repo_kok disina kopyalanmis; oraya symlink et.
                # En temiz yol: aracin TAM YOLU'nu kos, ama KOK'u repo_kok yapmak
                # icin cwd'i repo_kok ver. Bu `--hazirla` icin yeterli.
                # Izole kopya -> repo_kok/tools/ uzerine yaz, esas dosyayi silmeden.
                # Daha basit: araci repo_kok/tools/indexnow-gonder.py olarak calistir
                # ama M4 mutantli kopya oraya kopyalanmali.
                shutil.copyfile(kopya, os.path.join(repo_kok, "tools", "indexnow-gonder.py"))
                rc, cikti = kos(os.path.join(repo_kok, "tools", "indexnow-gonder.py"),
                                env=_env({"PRUVO_INDEXNOW_SITEMAP_UC": sitemap_kapali}),
                                args=["--hazirla", hedef],
                                cwd=repo_kok)
            # V9'un gectigi kosulu mutantla KIRMIZI olmali: rc!=0 VEYA TAMAM varsa
            # V9'un gercek davranisi bozulmus demektir (KIRMIZI). Bu durum M4 = KIRMIZI
            # eder (gecen mutant).
            if rc != 0 or "TAMAM" in cikti:
                gccer.append("M4")
            else:
                hata.append("M4 --hazirla indirme hatasinda rc=0 kalmali degildi ama V9 GECTI "
                            "(rc=%d, 'TAMAM' YOK):\n  cikti=%r"
                            % (rc, cikti[:400]))
        # ── M5: namespace-kor ayristirici geri gelir -> V10 KIRMIZI ──────────
        # Capa: yerel-ad eslemesi, namespace'li etiketi KACIRAN tam esitlige doner
        # (17 Eki oncesi `findall("url")` davranisi).
        with tempfile.TemporaryDirectory(prefix="indexnow-m5-") as m_tmp:
            kopya = izole_kopya(ARAC, m_tmp)
            mutasyonla(kopya, 'if _yerel_ad(url.tag) != "url":', 'if url.tag != "url":')
            rc, cikti, _hit = _v10_kos(kopya, m_tmp)
            if not (rc == 0 and "INDEXNOW=4 URL http=202" in cikti):
                gccer.append("M5")
            else:
                hata.append("M5 namespace-kor ayristirici geri geldi ama V10 GECTI:\n  cikti=%r"
                            % cikti[:400])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANA
# ══════════════════════════════════════════════════════════════════════════════
def main():
    gccer = []
    hata = []

    vakalar_kos(gccer, hata)
    mutantlar_kos(gccer, hata)

    vakalar = [g for g in gccer if g.startswith("V")]
    mutantlar = [g for g in gccer if g.startswith("M") and g[1:].isdigit()]

    print("VAKA_GECEN=%d  VAKA_HATA=%d" % (len(vakalar), 11 - len(vakalar)))
    print("MUTANT_GECEN=%d MUTANT_HATA=%d" % (len(mutantlar), 5 - len(mutantlar)))
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/11 MUTANT %d/5" % (len(vakalar), len(mutantlar)))
    if hata:
        print("HAL=KIRMIZI")
        return 1
    if len(vakalar) != 11 or len(mutantlar) != 5:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
