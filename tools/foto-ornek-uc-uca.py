#!/usr/bin/env python3
"""FOTO `ORNEK-` UCTAN UCA KABUL (8 Eki 2026; BaBa 00:3x hukmu 1(b), OKAN EMRI 00:1x olcut 1-6).

Bir kategoride (foto turu) zinciri ONIZLEMEDE olcer; her olcut HAZIR/EKSIK + sayi basar:
  (1) secim+galeri : tur manifestte + gecerli ornegi var + ornek gorselleri R2'de 200 (image/*) +
                     onizleme worker'inda `/api/shop/foto/acik` turu listeliyor (D1 `foto_acik` + turHazir)
  (2) onizleme     : ORNEK isi (`foto_isler.ziyaretci='ornek'`) -> kopru (foto-uretec-kosucu --hedef onizleme)
                     -> uretec onizlemesi `onizleme-hazir` + R2 onizleme.png >= 1024 px + olcu.json.
                     Tarayici onizleyicili tur (manifest TARAYICI_ONIZLEYICI, bugun litofan): sunucunun
                     /foto/litofan kurallarina uyan gri harita + (4)'te uretecin onizleme.png'si.
  (3) surgu+fiyat  : /acik olculeri == VERI.olcuSecenekleri ve her olcude fiyat == mm x 1000 kurus
                     (formul `mm_x_10tl`, VERI.fiyatKurus ile ayni) + tarayicida #foto-olcu surgusu en uc
                     olcude "<mm> mm → <TL> TL" yaziyor
  (4) ORNEK siparis: odemesiz `ORNEK-<is ilk 12>` uretim satiri (kalem 0) -> kopru -> uretec -> 3MF ->
                     asama 'hazir' + panel listesi (panelOrnekListe sorgusu) kaydi; 3MF BAGIMSIZ olculur:
                     her nesne su gecirmez (her yonlu kenar tam 1 kez + tersi var) + dunya kutusunun en uzun
                     ekseni olcu_mm +-%1 + olcu.json alanlari dolu (model_sha256 == 3MF sha256)
  (5) aydinlatma   : manifest durustluk + ornek_notu + aydinlatma maddeleri dolu; sunucu onaysiz istegi 400
                     `onay-yok` ile REDDEDER, onayli istek onaya takilmaz (403 bot-dogrulama: yazim 0);
                     tarayicida aydinlatma kutusunda TEK onay kutusu + onaysiz dugme KAPALI + durustluk metni
  (6) 375 px       : mobil emulasyonda (375x812, mobile) tur secili iken yatay tasma 0 + konsol hatasi 0

MUTANT (her kosumda, olcutun on kosulu): acik OLMAYAN bir kategoriye (manifest - /acik; hepsi aciksa galeri
yer tutucusu `figur`) onizleme istegi -> sunucu 400 DEMELI. Demezse betik GECERSIZ (rc 2, HAZIR=0).

Son satir: `HAZIR=<n>/<kosulan> rc=<k>` — rc 0 hepsi HAZIR · 1 EKSIK var · 2 gecersiz/yapilandirma.
Tur listesi MANIFESTTEN okunur (`--hepsi` / `--kol D`); sabit liste YOK — TeKiN'in yeni kopru kayitlari
manifeste girince ayni betik kosar.

YAZIM SINIRI: yalniz ONIZLEME D1/kovasi (shop/wrangler.onizleme.toml; canli adlarla ayniysa DUR). Canli
D1'e, odemeye, urunler.json'a yazim YOK. Yerel iz: tempfile dizinleri (try/finally silinir).
Test kancalari: FOTO_UU_TABAN · FOTO_UU_WRANGLER · FOTO_UU_KOSUCU · FOTO_UU_MEDYA_ESLE (onek=onek) ·
FOTO_UU_CHROME ("0" = tarayici yok -> (3)(5)(6) OLCULEMEDI) · FOTO_UU_BEKLE_SN (429 bekleme) ·
FOTO_UU_TARAYICI_SAHTE (tarayici sonucu JSON dosyasi; yalniz hermetik test).
Kabul: tools/foto-ornek-uc-uca-test.py (sahte sunucu + sahte wrangler; mutantlar izole kopyada).
"""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import secrets
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
MANIFEST = os.path.join(KOK, "foto-uretim-veri.js")
ONIZLEME_TOML = os.path.join(SHOP, "wrangler.onizleme.toml")
CANLI_TOML = os.path.join(SHOP, "wrangler.toml")
VARSAYILAN_TABAN = "https://foto-onizleme-pruvo-shop.gmlmz.workers.dev"
ORNEK_ZIYARETCI = "ornek"          # shop/src/foto.js ORNEK_ZIYARETCI
ORNEK_SIPARIS_ONEK = "ORNEK-"      # shop/src/foto.js ORNEK_SIPARIS_ONEK
YER_TUTUCU_TUR = "figur"           # galeride tur tanimi olmayan yer tutucu (foto-uretim.js)
ONIZLEME_MIN_PX = 1024
TOLERANS = {"D": 0.01, "R": 0.03}
OLCUTLER = ["1", "2", "3", "4", "5", "6"]
ETIKET = {"1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤", "6": "⑥"}

NODE_MANIFEST = r"""
const vm=require('vm'),fs=require('fs');const k={};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});
const F=k.PRUVO_FOTO, mod=process.argv[2];
if(mod==='dok'){
 const out={onay_surum:F.onay_surum,turler:F.turler.map(t=>({kod:t.kod,ad:t.ad,motor:t.motor,kol:F.kolu(t.kod),
  uretec:t.uretec,girdi:t.girdi||[],girdi_acik:(t.girdi||[]).map(x=>!!(F.GIRDI_TURLERI[x]&&F.GIRDI_TURLERI[x].acik===true)),
  form:t.form||{},olcu_mm:t.olcu_mm||null,olcu_secenekleri:F.olcuSecenekleri(t.kod),
  fiyatlar:F.olcuSecenekleri(t.kod).map(mm=>[mm,F.fiyatKurus(t.kod,mm),F.fiyatSatiri(t.kod,mm)]),
  formul:t.fiyat?t.fiyat.formul:'',formul_kurus_mm:t.fiyat?(F.FIYAT_FORMULLERI[t.fiyat.formul]||null):null,
  ornekler:F.ornekler.filter(o=>o.tur===t.kod&&F.ornekGecerli(o)).map(o=>({kanit:F.ornekKaniti(o),
   gorseller:[o.foto,o.onizleme,o.baski,o.render].filter(Boolean)})),
  renk_bolgeleri:t.renk_bolgeleri||[],malzemeler:t.malzemeler||{},durustluk:t.durustluk||'',
  ornek_notu:t.ornek_notu||'',aydinlatma:F.aydinlatmaMaddeleri(t.kod),
  tarayici_onizleyici:!!(F.TARAYICI_ONIZLEYICI&&F.TARAYICI_ONIZLEYICI[t.uretec]===true)}))};
 process.stdout.write(JSON.stringify(out));
} else {
 const g=JSON.parse(process.argv[3]);const r={};
 for(const kod of Object.keys(g)){r[kod]=F.parametreDogrula(kod,g[kod]);}
 process.stdout.write(JSON.stringify(r));
}
"""


class Ayar(Exception):
    """Yapilandirma/erisim hatasi -> rc 2 (olcum yapilamadi; yesil SAYILMAZ)."""


def simdi_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def sql_metin(v):
    return "'" + str(v).replace("'", "''") + "'"


# ------------------------------------------------------------------ manifest (node, tek kaynak)
def manifest_oku(mod="dok", ek=None):
    arg = ["node", "-e", NODE_MANIFEST, MANIFEST, mod] + ([json.dumps(ek, ensure_ascii=False)] if ek is not None else [])
    p = subprocess.run(arg, capture_output=True, text=True)
    if p.returncode != 0:
        raise Ayar("manifest okunamadi: " + p.stderr.strip()[:300])
    return json.loads(p.stdout)


# ------------------------------------------------------------------ hedef: yalniz ONIZLEME
def hedef_adlari():
    """(d1, kova) onizleme toml'dan; canli toml'daki adlarla ayniysa DUR (canliya test yuku YASAK)."""
    def oku(yol):
        with open(yol, encoding="utf-8") as f:
            s = f.read()
        db = re.search(r'(?m)^database_name\s*=\s*"([a-z0-9-]+)"', s)
        kova = re.search(r'binding\s*=\s*"OZEL_DOSYA"\s*\n\s*bucket_name\s*=\s*"([a-z0-9-]+)"', s)
        return (db.group(1) if db else ""), (kova.group(1) if kova else "")
    try:
        d1, kova = oku(ONIZLEME_TOML)
        cd1, ckova = oku(CANLI_TOML)
    except OSError as e:
        raise Ayar("toml okunamadi: %s" % e)
    if not d1 or not kova or d1 == cd1 or kova == ckova:
        raise Ayar("onizleme D1/kova canlidan ayri degil (d1=%s kova=%s) — canliya yazilmaz" % (d1, kova))
    return d1, kova


def hesap_kimligi():
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        return os.environ["CLOUDFLARE_ACCOUNT_ID"]
    try:
        with open(os.path.join(KOK, "tools", "foto-onizleme.py"), encoding="utf-8") as f:
            m = re.search(r'(?m)^HESAP\s*=\s*"([0-9a-f]{32})"', f.read())
        return m.group(1) if m else ""
    except OSError:
        return ""


class Bulut:
    """Onizleme D1 + kova (wrangler alt sureci; yerel OAuth, secret OKUNMAZ)."""

    def __init__(self, d1, kova):
        self.d1_ad, self.kova = d1, kova
        k = os.environ.get("FOTO_UU_WRANGLER", "")
        self.komut = shlex.split(k) if k else ["npx", "--prefix", SHOP, "wrangler"]
        self.env = dict(os.environ)
        h = hesap_kimligi()
        if h:
            self.env["CLOUDFLARE_ACCOUNT_ID"] = h

    def wr(self, arg, zaman=180):
        try:
            return subprocess.run(self.komut + arg, cwd=SHOP, capture_output=True, text=True, timeout=zaman,
                                  env=self.env)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Ayar("wrangler: %s" % e)

    def sql(self, q):
        p = self.wr(["d1", "execute", self.d1_ad, "--remote", "--json", "--command", q])
        if p.returncode != 0:
            raise Ayar("d1: " + (p.stderr or p.stdout).strip()[-300:])
        try:
            v = json.loads(p.stdout)
            blok = v[0] if isinstance(v, list) else v
        except (ValueError, IndexError):
            raise Ayar("d1-json")
        if not isinstance(blok, dict) or blok.get("success") is False:
            raise Ayar("d1-basarisiz")
        return blok.get("results") or []

    def koy(self, anahtar, yol, tur):
        p = self.wr(["r2", "object", "put", self.kova + "/" + anahtar, "--remote", "--file", yol,
                     "--content-type", tur])
        if p.returncode != 0:
            raise Ayar("r2-put: " + (p.stderr or p.stdout).strip()[-200:])

    def al(self, anahtar, hedef):
        p = self.wr(["r2", "object", "get", self.kova + "/" + anahtar, "--remote", "--file", hedef])
        return p.returncode == 0 and os.path.isfile(hedef)


# ------------------------------------------------------------------ HTTP
def http(yontem, url, govde=None, zaman=30):
    """Donus (kod, baslik_tur, govde_bayt). Ag hatasi -> (0, '', b'')."""
    esle = os.environ.get("FOTO_UU_MEDYA_ESLE", "")
    if "=" in esle:
        a, b = esle.split("=", 1)
        if url.startswith(a):
            url = b + url[len(a):]
    veri = json.dumps(govde).encode() if govde is not None else None
    r = urllib.request.Request(url, data=veri, method=yontem,
                               headers={"User-Agent": "pruvo-ornek-uc-uca/1", "Content-Type": "application/json",
                                        "Origin": taban()})
    try:
        with urllib.request.urlopen(r, timeout=zaman) as y:
            return y.status, y.headers.get("Content-Type", ""), y.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", e.read()
    except (urllib.error.URLError, OSError, ValueError):
        return 0, "", b""


def taban():
    return os.environ.get("FOTO_UU_TABAN", VARSAYILAN_TABAN).rstrip("/")


def json_coz(b):
    try:
        v = json.loads(b.decode("utf-8"))
        return v if isinstance(v, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def post_429(yol, govde):
    """Hiz siniri (429 cok-istek) gelirse bekleyip tekrar dener (en cok 4)."""
    bekle = float(os.environ.get("FOTO_UU_BEKLE_SN", "20"))
    for _ in range(5):
        k, _, b = http("POST", taban() + yol, govde)
        if k != 429 or json_coz(b).get("hata") not in ("cok-istek",):
            return k, json_coz(b)
        time.sleep(bekle)
    return k, json_coz(b)


# ------------------------------------------------------------------ ornek girdiler (deterministik)
def png_yaz(w, h, piksel):
    """Gri tonlu PNG (stdlib). piksel(x, y) -> 0..255."""
    satirlar = b"".join(b"\x00" + bytes(piksel(x, y) for x in range(w)) for y in range(h))

    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(satirlar, 9)) + ch(b"IEND", b""))


def ornek_foto():
    """640x480: acik zeminde koyu dolu elips (kontrastli, tek ada) — muhur/sablon/yapboz/plaket girdisi.
    Zemin hafif desenli: sunucu GORSEL_EN_AZ_BAYT (2 KB) altindaki gorseli reddeder (duz zemin ~1 KB)."""
    return png_yaz(640, 480, lambda x, y: 25 if ((x - 320) / 210.0) ** 2 + ((y - 240) / 150.0) ** 2 <= 1
                   else 228 + (x * 7919 + y * 104729) % 13)


def ornek_gri_harita():
    """400x300 gri harita (sunucu /foto/litofan kurali: PNG, uzun kenar <= 1200, oran <= 5)."""
    return png_yaz(400, 300, lambda x, y: (x * 255 // 399 + y * 120 // 299) % 256)


ORNEK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><path d="M10 10 H90 V50 H10 Z '
             'M30 20 V40 H70 V20 Z" fill="#000" fill-rule="evenodd"/></svg>')


# Bilesen tiplerin ornek degerleri (dosya YOK): ses = 100 elemanli sinus genlik dizisi (0..1),
# konum/tarih = semanin `ornek`/`varsayilan` degeri, yoksa sabit ornek (VERI.parametreDogrula sinirlarinda).
ORNEK_GENLIK = [round(0.5 + 0.45 * math.sin(i * 2 * math.pi / 25), 4) for i in range(100)]
ORNEK_KONUM = {"enlem": 41.0082, "boylam": 28.9784}
ORNEK_TARIH = {"tarih": "2026-10-07", "saat": "21:30", "utc_ofset_saat": 3}


def olcu_sec(t):
    s = t.get("olcu_secenekleri") or []
    return s[len(s) // 2] if s else None


def ornek_parametre(t, olcu):
    """Form semasindan GECERLI ornek parametre (dogrulamayi VERI.parametreDogrula yapar). Desteklenmeyen
    tip -> None (olcut EKSIK, sebep adiyla)."""
    p = {}
    for ad, s in (t.get("form") or {}).items():
        tip = s.get("tip")
        if tip == "secim":
            p[ad] = (s.get("secenekler") or [None])[0]
        elif tip == "sayi":
            mn, mx, adim = s.get("min", 0), s.get("max", 0), s.get("adim") or 1
            hedef = min(mx, max(mn, (olcu or mn) // 2))
            p[ad] = mn + ((hedef - mn) // adim) * adim
        elif tip == "metin":
            if s.get("zorunlu") is False:
                continue
            p[ad] = "https://pruvo3d.com" if s.get("bayt_max") else "PRUVO"
        elif tip == "url":
            p[ad] = "https://pruvo3d.com"
        elif tip == "bool":
            p[ad] = s.get("varsayilan") is True
        elif tip == "ses":
            p[ad] = list(ORNEK_GENLIK)
        elif tip == "konum":
            k = s.get("ornek") or s.get("varsayilan") or ORNEK_KONUM
            p[ad] = {"enlem": k["enlem"], "boylam": k["boylam"]}
        elif tip == "tarih":
            k = s.get("ornek") or s.get("varsayilan") or ORNEK_TARIH
            if isinstance(k, str):
                k = dict(ORNEK_TARIH, tarih=k)
            p[ad] = dict(k) if s.get("saat") is True else k["tarih"]
        else:
            return None, "form-tipi-desteksiz:%s" % tip
    return p, ""


def ornek_secim(t):
    sc = {}
    for b in t.get("renk_bolgeleri") or []:
        if b.get("renkler"):
            sc[b["kod"] + "_renk"] = b["renkler"][0]
    for bolge, liste in (t.get("malzemeler") or {}).items():
        if liste:
            sc[bolge + "_malzeme"] = liste[0]
    return sc


def ornek_dosyalar(t):
    """Turun girdisine gore dosyalar {anahtar: (ad, bayt, tip)}; desteklenmeyen girdi -> None."""
    d = {}
    for g in t.get("girdi") or []:
        if g in ("foto-1", "foto-1-3"):
            d["foto"] = ("foto.png", ornek_foto(), "image/png")
        elif g == "svg":
            d["svg"] = ("svg.svg", ORNEK_SVG.encode(), "image/svg+xml")
        elif g in ("form", "metin", "url", "ses", "konum", "tarih"):
            continue  # degeri form parametresi tasir (ses = genlik dizisi; dosya YOK)
        else:
            return None, "girdi-desteksiz:%s" % g
    return d, ""


# ------------------------------------------------------------------ 3MF bagimsiz olcum
def uc_mf_olc(yol):
    """Donus {nesne, sizdirmaz_nesne, kutu:(x,y,z), uzun} — kosucudan BAGIMSIZ. Okunamazsa None."""
    try:
        with zipfile.ZipFile(yol) as z:
            ad = [n for n in z.namelist() if n.endswith(".model")]
            xml = z.read(ad[0]).decode("utf-8") if ad else ""
    except (OSError, KeyError, IndexError, zipfile.BadZipFile, UnicodeDecodeError):
        return None
    nesne = {}
    for m in re.finditer(r"<object\b([^>]*)>(.*?)</object>", xml, re.S):
        oid = re.search(r'\bid="(\d+)"', m.group(1))
        if not oid:
            continue
        vs = [tuple(round(float(c), 4) for c in v) for v in re.findall(
            r'<vertex\s+x="([-0-9.eE+]+)"\s+y="([-0-9.eE+]+)"\s+z="([-0-9.eE+]+)"', m.group(2))]
        ts = [tuple(int(c) for c in t) for t in re.findall(
            r'<triangle\s+v1="(\d+)"\s+v2="(\d+)"\s+v3="(\d+)"', m.group(2))]
        komp = re.findall(r'<component\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', m.group(2))
        nesne[oid.group(1)] = (vs, ts, komp)

    def sizdirmaz(vs, ts):
        kenar = {}
        for t in ts:
            try:
                k = [vs[i] for i in t]
            except IndexError:
                return False
            for a, b in ((k[0], k[1]), (k[1], k[2]), (k[2], k[0])):
                kenar[(a, b)] = kenar.get((a, b), 0) + 1
        return bool(kenar) and all(n == 1 and kenar.get((b, a)) == 1 for (a, b), n in kenar.items())

    def donustur(p, t):
        if not t:
            return p
        a = [float(x) for x in t.split()]
        return (p[0] * a[0] + p[1] * a[3] + p[2] * a[6] + a[9], p[0] * a[1] + p[1] * a[4] + p[2] * a[7] + a[10],
                p[0] * a[2] + p[1] * a[5] + p[2] * a[8] + a[11])

    def noktalar(oid, t, d=0):
        if oid not in nesne or d > 8:
            return []
        vs, _, komp = nesne[oid]
        out = list(vs)
        for cid, ct in komp:
            out += noktalar(cid, ct, d + 1)
        return [donustur(p, t) for p in out]

    agli = [k for k, (vs, ts, _) in nesne.items() if ts]
    mn, mx = [float("inf")] * 3, [float("-inf")] * 3
    parca = []  # her build ogesinin kendi dunya kutusu (tabla duzeninde parca = urunun bir parcasi)
    for b in re.finditer(r'<item\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', xml):
        pm, px = [float("inf")] * 3, [float("-inf")] * 3
        for p in noktalar(b.group(1), b.group(2)):
            for i in range(3):
                mn[i], mx[i] = min(mn[i], p[i]), max(mx[i], p[i])
                pm[i], px[i] = min(pm[i], p[i]), max(px[i], p[i])
        if pm[0] != float("inf"):
            parca.append(max(px[i] - pm[i] for i in range(3)))
    if not agli or mn[0] == float("inf"):
        return None
    kutu = tuple(round(mx[i] - mn[i], 3) for i in range(3))
    return {"nesne": len(agli), "sizdirmaz_nesne": sum(1 for k in agli if sizdirmaz(nesne[k][0], nesne[k][1])),
            "kutu": kutu, "uzun": max(kutu), "parca": len(parca), "parca_en_uzun": round(max(parca), 3)}


def png_boyut(yol):
    try:
        with open(yol, "rb") as f:
            b = f.read(24)
    except OSError:
        return None
    if len(b) < 24 or b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])


# ------------------------------------------------------------------ tarayici (CDP, stdlib websocket)
class Cdp:
    def __init__(self, ws_url):
        m = re.match(r"ws://([^:/]+):(\d+)(/.*)", ws_url)
        self.s = socket.create_connection((m.group(1), int(m.group(2))), timeout=30)
        anahtar = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET %s HTTP/1.1\r\nHost: %s:%s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                        % (m.group(3), m.group(1), m.group(2), anahtar)).encode())
        yanit = b""
        while b"\r\n\r\n" not in yanit:
            yanit += self.s.recv(4096)
        self.artik = yanit.split(b"\r\n\r\n", 1)[1]
        self.no = 0
        self.olaylar = []

    def _oku(self, n):
        while len(self.artik) < n:
            c = self.s.recv(65536)
            if not c:
                raise Ayar("cdp baglanti kapandi")
            self.artik += c
        v, self.artik = self.artik[:n], self.artik[n:]
        return v

    def _mesaj(self):
        veri = b""
        while True:
            b1, b2 = self._oku(2)
            n = b2 & 0x7f
            if n == 126:
                n = struct.unpack(">H", self._oku(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._oku(8))[0]
            veri += self._oku(n)
            if b1 & 0x80:
                return json.loads(veri.decode("utf-8"))

    def gonder(self, yontem, **param):
        self.no += 1
        b = json.dumps({"id": self.no, "method": yontem, "params": param}).encode()
        bas = bytes([0x81]) + (bytes([0x80 | len(b)]) if len(b) < 126 else
                               bytes([0x80 | 126]) + struct.pack(">H", len(b)) if len(b) < 65536 else
                               bytes([0x80 | 127]) + struct.pack(">Q", len(b)))
        mask = os.urandom(4)
        self.s.sendall(bas + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(b)))
        while True:
            m = self._mesaj()
            if m.get("id") == self.no:
                return m.get("result") or {}
            if "method" in m:
                self.olaylar.append(m)

    def js(self, ifade):
        r = self.gonder("Runtime.evaluate", expression=ifade, returnByValue=True, awaitPromise=True)
        return (r.get("result") or {}).get("value")

    def hatalar(self):
        n = []
        for o in self.olaylar:
            m, p = o.get("method"), o.get("params") or {}
            if m == "Runtime.exceptionThrown":
                n.append("istisna: " + str((p.get("exceptionDetails") or {}).get("text", ""))[:120])
            elif m == "Runtime.consoleAPICalled" and p.get("type") == "error":
                n.append("console.error: " + str([a.get("value") for a in p.get("args") or []])[:120])
            elif m == "Log.entryAdded" and (p.get("entry") or {}).get("level") == "error":
                n.append("log: " + str((p.get("entry") or {}).get("text", ""))[:120] + " " +
                         str((p.get("entry") or {}).get("url", ""))[:80])
        return n


def chrome_yolu():
    v = os.environ.get("FOTO_UU_CHROME", "")
    if v == "0":
        return ""
    for y in (v, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if y and os.path.isfile(y):
            return y
    return ""


TARAYICI_JS = r"""
(async () => {
  const kod = %(kod)s, bekle = (ms) => new Promise(r => setTimeout(r, ms));
  const b = document.getElementById('fotoUretim');
  if (!b) return {hata: 'bolum-yok'};
  b.scrollIntoView();
  let radyo = null, tek = false;
  for (let i = 0; i < 60; i++) {
    radyo = document.getElementById('foto-tur-' + kod);
    tek = !!document.getElementById('foto-olcu') && !document.querySelector('input[name="foto-tur"]');
    if (radyo || tek) break;
    await bekle(250);
  }
  if (!radyo && !tek) return {hata: 'tur-secilemiyor'};
  if (radyo) { radyo.click(); await bekle(300); }
  const surgu = document.getElementById('foto-olcu');
  let fiyat = '';
  if (surgu) {
    surgu.value = surgu.max; surgu.dispatchEvent(new Event('input', {bubbles: true}));
    await bekle(100);
    const y = surgu.parentNode.querySelector('.foto-uretim-surgu-fiyat'); fiyat = y ? y.textContent : '';
  }
  // Aydinlatma alani = <details> metni + altindaki onay kutusu (ayni kapsayici); TEK kutu olmali.
  const det = document.querySelector('#fotoUretim .foto-uretim-aydinlatma');
  const onay = document.getElementById('foto-aydinlatma-onay');
  const kap = det ? det.parentNode : null;
  const kutu = kap && onay && kap.contains(onay) ? kap.querySelectorAll('input[type=checkbox]').length : 0;
  if (onay && onay.checked) { onay.click(); await bekle(100); }
  const btn = document.querySelector('#fotoUretim .foto-uretim-s1-buton-sira button');
  const dp = document.querySelector('#fotoUretim .foto-uretim-durustluk p');
  await bekle(500);
  const d = document.documentElement;
  const fe = document.querySelector('#fotoUretim .foto-uretim-fiyat');
  const secili = fe ? (fe.getAttribute('data-tur') || '') : '';
  return {secildi: (!!radyo || tek) && secili === kod, secili_tur: secili, surgu: !!surgu, fiyat: fiyat, onay_kutusu: kutu,
          onaysiz_dugme_kapali: !!btn && btn.disabled === true, durustluk: dp ? dp.textContent : '',
          tasma: Math.max(d.scrollWidth - d.clientWidth, document.body.scrollWidth - d.clientWidth),
          genislik: d.clientWidth};
})()
"""


def tarayici_olc(kodlar):
    """{kod: sonuc dict | {'hata': ...}}. Chrome yoksa {} (olcutler OLCULEMEDI)."""
    sahte = os.environ.get("FOTO_UU_TARAYICI_SAHTE", "")
    if sahte:  # yalniz hermetik test: tarayici sonucu dosyadan
        with open(sahte, encoding="utf-8") as f:
            return json.load(f)
    yol = chrome_yolu()
    if not yol:
        return {}
    veri = tempfile.mkdtemp(prefix="foto-uu-chrome-")
    p = None
    sonuc = {}
    try:
        p = subprocess.Popen([yol, "--headless=new", "--remote-debugging-port=0", "--user-data-dir=" + veri,
                              "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                              "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_dosya = os.path.join(veri, "DevToolsActivePort")
        for _ in range(100):
            if os.path.isfile(port_dosya) and open(port_dosya).read().strip():
                break
            time.sleep(0.1)
        port = open(port_dosya).read().split()[0]
        for kod in kodlar:
            r = urllib.request.Request("http://127.0.0.1:%s/json/new?about:blank" % port, method="PUT")
            with urllib.request.urlopen(r, timeout=10) as y:
                hedef = json.loads(y.read())
            c = Cdp(hedef["webSocketDebuggerUrl"])
            try:
                c.gonder("Runtime.enable")
                c.gonder("Log.enable")
                c.gonder("Page.enable")
                c.gonder("Emulation.setDeviceMetricsOverride", width=375, height=812, deviceScaleFactor=2,
                         mobile=True)
                c.gonder("Emulation.setTouchEmulationEnabled", enabled=True)
                c.gonder("Page.navigate", url=taban() + "/")
                for _ in range(80):
                    if c.js("document.readyState") == "complete":
                        break
                    time.sleep(0.25)
                v = c.js(TARAYICI_JS % {"kod": json.dumps(kod)}) or {"hata": "js-sonuc-yok"}
                time.sleep(0.5)
                c.js("1")  # bekleyen olaylari topla
                v["konsol"] = c.hatalar()
                sonuc[kod] = v
            finally:
                c.s.close()
    except (OSError, ValueError, KeyError, Ayar, urllib.error.URLError) as e:
        for kod in kodlar:
            sonuc.setdefault(kod, {"hata": "tarayici: %s" % e})
    finally:
        if p:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
        shutil.rmtree(veri, ignore_errors=True)
    return sonuc


# ------------------------------------------------------------------ kosucu (kopru)
def kosucu_kos():
    yol = os.environ.get("FOTO_UU_KOSUCU") or os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
    env = dict(os.environ)
    h = hesap_kimligi()
    if h:
        env["CLOUDFLARE_ACCOUNT_ID"] = h
    if os.environ.get("FOTO_UU_WRANGLER"):
        env["FOTO_KOSUCU_WRANGLER"] = os.environ["FOTO_UU_WRANGLER"]
    env.setdefault("FOTO_KOSUCU_PYTHON", sys.executable)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for _ in range(10):
        p = subprocess.run([sys.executable, yol, "--hedef", "onizleme", "--uygula"], capture_output=True, text=True,
                           env=env, timeout=3600)
        son = (p.stdout.strip().splitlines() or [""])[-1]
        if not son.startswith("HAL=KILITLI"):
            return son, p.stdout + p.stderr
        time.sleep(15)
    return son, p.stdout + p.stderr


# ------------------------------------------------------------------ olcum
class Tur:
    def __init__(self, kod, t):
        self.kod, self.t = kod, t
        self.s = {o: (False, "OLCULEMEDI") for o in OLCUTLER}
        self.is_no = ""
        self.olcu = None
        self.parametre, self.secim, self.dosyalar = {}, {}, {}
        self.hazirlik = ""

    def koy(self, o, gecti, ac):
        self.s[o] = (bool(gecti), ac)

    def hazir(self):
        return all(self.s[o][0] for o in OLCUTLER)


def olc_1(tr, acik_kodlar):
    t = tr.t
    orn = t.get("ornekler") or []
    gorseller = sorted({g for o in orn for g in o["gorseller"]})
    tamam = 0
    for g in gorseller:
        k, tip, _ = http("GET", g)
        tamam += 1 if k == 200 and tip.startswith("image/") else 0
    girdi_acik = all(t.get("girdi_acik") or [False])
    ok = bool(orn) and gorseller and tamam == len(gorseller) and tr.kod in acik_kodlar and girdi_acik
    tr.koy("1", ok, "ornek=%d gorsel_200=%d/%d acik=%d girdi_acik=%d" % (
        len(orn), tamam, len(gorseller), 1 if tr.kod in acik_kodlar else 0, 1 if girdi_acik else 0))


def hazirla(tr):
    t = tr.t
    tr.olcu = olcu_sec(t)
    if tr.olcu is None:
        tr.hazirlik = "olcu-yok"
        return
    p, h = ornek_parametre(t, tr.olcu)
    d, h2 = ornek_dosyalar(t)
    if p is None or d is None:
        tr.hazirlik = h or h2
        return
    tr.parametre, tr.dosyalar, tr.secim = p, d, ornek_secim(t)


def onizleme_isi_yaz(tr, bulut, gecici):
    """ORNEK isi: shop/src/foto.js musteri ucunun satir+dosya bicimi, ziyaretci='ornek' (panel ORNEK kolu)."""
    t = tr.t
    tr.is_no = secrets.token_hex(16)
    simdi = simdi_iso()
    onay = "onay_tarih, onay_surum", "%s, %s" % (sql_metin(simdi), sql_metin(MAN["onay_surum"]))
    if t.get("tarayici_onizleyici"):
        yol = os.path.join(gecici, tr.is_no + ".png")
        with open(yol, "wb") as f:
            f.write(ornek_gri_harita())
        bulut.koy("foto-onizleme/%s.png" % tr.is_no, yol, "image/png")
        bulut.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, kredi, %s)"
                  " VALUES (%s, %s, %d, %s, %s, 'hazir', %s, 0, %s)" % (
                      onay[0], sql_metin(tr.is_no), sql_metin(tr.kod), tr.olcu, sql_metin(ORNEK_ZIYARETCI),
                      sql_metin(simdi), sql_metin(simdi), onay[1]))
        return
    renk, malz = {}, {}
    for b in t.get("renk_bolgeleri") or []:
        if tr.secim.get(b["kod"] + "_renk"):
            renk[b["kod"]] = tr.secim[b["kod"] + "_renk"]
    for bolge in t.get("malzemeler") or {}:
        if tr.secim.get(bolge + "_malzeme"):
            malz[bolge] = tr.secim[bolge + "_malzeme"]
    beyan = {}
    for anahtar, (ad, bayt, tip) in tr.dosyalar.items():
        yol = os.path.join(gecici, tr.is_no + "-" + ad)
        with open(yol, "wb") as f:
            f.write(bayt)
        bulut.koy("foto-uretec-onizleme/%s/%s" % (tr.is_no, ad), yol, tip)
        beyan[anahtar] = ad
    girdi = {"sozlesme": 1, "kategori": tr.kod, "siparis_no": "", "kalem": 0, "olcu_mm": tr.olcu,
             "renkler": renk, "malzemeler": malz, "parametreler": tr.parametre, "dosyalar": beyan}
    yol = os.path.join(gecici, tr.is_no + "-girdi.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(girdi, f, ensure_ascii=False)
    bulut.koy("foto-uretec-onizleme/%s/girdi.json" % tr.is_no, yol, "application/json")
    bulut.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol, hata, %s)"
              " VALUES (%s, %s, %d, %s, %s, 'uretec-onizleme', 0, '', %s)" % (
                  onay[0], sql_metin(tr.is_no), sql_metin(tr.kod), tr.olcu, sql_metin(ORNEK_ZIYARETCI),
                  sql_metin(simdi), onay[1]))


def olc_2(tr, bulut, gecici):
    t = tr.t
    r = bulut.sql("SELECT asama, hata FROM foto_isler WHERE is_no = %s" % sql_metin(tr.is_no))
    asama = r[0]["asama"] if r else "yok"
    if t.get("tarayici_onizleyici"):
        b = png_boyut(os.path.join(gecici, tr.is_no + ".png"))
        ok = asama == "hazir" and b and max(b) <= 1200 and max(b) <= 5 * min(b)
        tr.koy("2", ok, "kol=tarayici gri_harita=%s asama=%s (uretec onizlemesi ④'te)" % (
            "%dx%d" % b if b else "yok", asama))
        return
    oy = os.path.join(gecici, tr.is_no + "-onizleme.png")
    jy = os.path.join(gecici, tr.is_no + "-olcu.json")
    var = asama == "onizleme-hazir" and bulut.al("foto-uretec-onizleme/%s/onizleme.png" % tr.is_no, oy)
    b = png_boyut(oy) if var else None
    olcu = {}
    if asama == "onizleme-hazir" and bulut.al("foto-uretec-onizleme/%s/olcu.json" % tr.is_no, jy):
        try:
            olcu = json.load(open(jy, encoding="utf-8"))
        except ValueError:
            olcu = {}
    ok = bool(b) and max(b) >= ONIZLEME_MIN_PX and olcu.get("kategori") == tr.kod and olcu.get("sozlesme") == 1
    tr.koy("2", ok, "asama=%s hata=%s onizleme_px=%s olcu.json=%d" % (
        asama, (r[0].get("hata") if r else "") or "-", "%dx%d" % b if b else "yok", 1 if olcu else 0))


def ornek_siparis_yaz(tr, bulut):
    simdi = simdi_iso()
    no = ORNEK_SIPARIS_ONEK + tr.is_no[:12]
    bulut.sql("INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel,"
              " onay_tarih, onay_surum) VALUES (%s, 0, %s, %s, %d, 'uretec-bekliyor', %s, %s, %s, %s)" % (
                  sql_metin(no), sql_metin(tr.is_no), sql_metin(tr.kod), tr.olcu, sql_metin(simdi),
                  sql_metin(simdi), sql_metin(simdi), sql_metin(MAN["onay_surum"])))


def olc_4(tr, bulut, gecici):
    no = ORNEK_SIPARIS_ONEK + tr.is_no[:12]
    # panelOrnekListe sorgusunun aynasi (shop/src/foto.js): panelde gorunen kayit.
    r = bulut.sql("SELECT i.is_no, i.tur, i.olcu_mm, i.tarih, i.asama AS onizleme, u.siparis_no, u.asama, u.sebep,"
                  " u.tarih AS u_tarih, u.guncel FROM foto_isler i LEFT JOIN foto_uretim u ON u.is_no = i.is_no AND"
                  " u.siparis_no LIKE 'ORNEK-%%' WHERE i.ziyaretci = %s AND i.is_no = %s" % (
                      sql_metin(ORNEK_ZIYARETCI), sql_metin(tr.is_no)))
    k = r[0] if r else {}
    kayit = (k.get("siparis_no") == no and k.get("asama") == "hazir" and k.get("tur") == tr.kod and
             k.get("olcu_mm") == tr.olcu and all(k.get(a) for a in ("tarih", "u_tarih", "guncel")))
    d = os.path.join(gecici, "siparis-" + tr.is_no)
    os.makedirs(d, exist_ok=True)
    dosya = {ad: os.path.join(d, ad) for ad in ("model.3mf", "olcu.json", "onizleme.png")}
    var = k.get("asama") == "hazir" and all(bulut.al("foto/%s/0/%s" % (no, ad), y) for ad, y in dosya.items())
    if not var:
        tr.koy("4", False, "siparis=%s asama=%s sebep=%s dosya=yok" % (no, k.get("asama"), k.get("sebep") or "-"))
        if tr.t.get("tarayici_onizleyici"):
            tr.koy("2", False, tr.s["2"][1] + " · uretec onizlemesi YOK")
        return
    try:
        olcu = json.load(open(dosya["olcu.json"], encoding="utf-8"))
    except ValueError:
        olcu = {}
    m = uc_mf_olc(dosya["model.3mf"])
    msha = hashlib.sha256(open(dosya["model.3mf"], "rb").read()).hexdigest()
    tol = TOLERANS.get(tr.t.get("motor"), 0)
    sizd = bool(m) and m["sizdirmaz_nesne"] == m["nesne"]
    uk = olcu.get("uzun_kenar_mm")
    # OLCEK EKSENI: tek montajli cikti -> tablanin dunya kutusunun en uzun ekseni == olcu_mm. Cok parcali
    # TABLA DUZENI (litofan panel+ayak, yapboz parcalari yan yana): tabla kutusu urun degildir -> montaj
    # boyutu kosucunun 3MF geometri olcumunden (olcu.json, tasima_mm duzeltmeli) +-tol VE bagimsiz kol:
    # hicbir parca urun olcusunu ASMAZ.
    eksen_yolu = "tabla"
    eksen = bool(m) and abs(m["uzun"] - tr.olcu) <= tr.olcu * tol + 1e-9
    if m and not eksen and m["parca"] > 1 and m["uzun"] > tr.olcu:
        eksen_yolu = "montaj"
        eksen = (m["parca_en_uzun"] <= tr.olcu * (1 + tol) + 1e-9 and isinstance(uk, (int, float)) and
                 abs(uk - tr.olcu) <= tr.olcu * tol + 1e-9)
    alanlar = (olcu.get("sozlesme") == 1 and olcu.get("kategori") == tr.kod and isinstance(uk, (int, float)) and
               abs(uk - tr.olcu) <= tr.olcu * tol + 1e-9 and olcu.get("sizdirmaz") is True and
               isinstance(olcu.get("renk_sayisi"), int) and 1 <= olcu["renk_sayisi"] <= 4 and
               all((olcu.get("kutu_mm") or {}).get(e, 0) > 0 for e in "xyz") and olcu.get("model_sha256") == msha)
    b = png_boyut(dosya["onizleme.png"])
    pv = bool(b) and max(b) >= ONIZLEME_MIN_PX
    tr.koy("4", kayit and sizd and eksen and alanlar and pv,
           "siparis=%s kayit=%d sizdirmaz=%s/%s kutu=%s uzun=%s eksen=%s parca=%s parca_en_uzun=%s hedef=%d±%g%% "
           "olcu.json_uzun=%s alanlar=%d onizleme=%s" % (
               no, 1 if kayit else 0, m["sizdirmaz_nesne"] if m else 0, m["nesne"] if m else 0,
               m["kutu"] if m else None, m["uzun"] if m else None, eksen_yolu if eksen else "YANLIS",
               m["parca"] if m else 0, m["parca_en_uzun"] if m else None, tr.olcu, tol * 100, uk,
               1 if alanlar else 0, "%dx%d" % b if b else "yok"))
    if tr.t.get("tarayici_onizleyici"):
        tr.koy("2", tr.s["2"][0] and pv, tr.s["2"][1] + " · uretec_onizleme=%s" % ("%dx%d" % b if b else "yok"))


def istek_govdesi(tr, onay):
    g = {"tur": tr.kod, "olcu_mm": tr.olcu}
    if onay:
        g["aydinlatma_onay"] = True
        g["onay_surum"] = MAN["onay_surum"]
    if tr.t.get("tarayici_onizleyici"):
        g["gorsel"] = "data:image/png;base64," + base64.b64encode(ornek_gri_harita()).decode()
        return "/api/shop/foto/litofan", g
    g["parametreler"] = tr.parametre
    g["secim"] = tr.secim
    if "foto" in tr.dosyalar:
        g["gorsel"] = "data:image/png;base64," + base64.b64encode(tr.dosyalar["foto"][1]).decode()
    if "svg" in tr.dosyalar:
        g["svg"] = tr.dosyalar["svg"][1].decode()
    return "/api/shop/foto/onizleme", g


def olc_3_5_6(tr, acik, tar):
    t = tr.t
    # (3) API: /acik olculeri == olcuSecenekleri ve fiyat == mm x formul (bagimsiz carpim).
    a = next((x for x in (acik.get("turler") or []) if x.get("kod") == tr.kod), None)
    beklenen = t.get("olcu_secenekleri") or []
    api_ok = (a is not None and t.get("formul") == "mm_x_10tl" and t.get("formul_kurus_mm") == 1000 and
              [o.get("mm") for o in a.get("olculer") or []] == beklenen and beklenen and
              all(o.get("fiyat_kurus") == o.get("mm") * 1000 for o in a.get("olculer") or []) and
              all(k == mm * 1000 for mm, k, _ in t.get("fiyatlar") or []))
    v = tar.get(tr.kod) if tar else None
    if v is not None and not v.get("secildi"):
        # Tur tarayicida SECILEMIYORSA (3)(5)(6) baska turun sayfasini olcerdi -> hepsi EKSIK, sebep adiyla.
        v = dict(v, surgu=False, onay_kutusu=0, hata=v.get("hata") or "secili_tur=%r" % v.get("secili_tur"))
    uc = beklenen[-1] if beklenen else 0
    beklenen_yazi = "%d mm → %s TL" % (uc, "{:,}".format(uc * 10).replace(",", "."))
    if not v:
        tr.koy("3", False, "api=%d tarayici=OLCULEMEDI" % (1 if api_ok else 0))
    else:
        sok = bool(v.get("surgu")) and v.get("fiyat") == beklenen_yazi
        tr.koy("3", api_ok and sok, "api=%d olcu=%d surgu=%d uc_yazi=%r beklenen=%r" % (
            1 if api_ok else 0, len(beklenen), 1 if v.get("surgu") else 0, v.get("fiyat"), beklenen_yazi))
    # (5) manifest + sunucu fail-closed + tarayici tek tik.
    man_ok = bool(t.get("durustluk")) and bool(t.get("ornek_notu")) and bool(t.get("aydinlatma"))
    yol, g = istek_govdesi(tr, False)
    k0, j0 = post_429(yol, g)
    yol, g = istek_govdesi(tr, True)
    k1, j1 = post_429(yol, g)
    sunucu_ok = k0 == 400 and j0.get("hata") == "onay-yok" and k1 == 403 and j1.get("hata") == "bot-dogrulama"
    ac = "manifest=%d onaysiz=%s/%s onayli=%s/%s" % (1 if man_ok else 0, k0, j0.get("hata"), k1, j1.get("hata"))
    if not v:
        tr.koy("5", False, ac + " tarayici=OLCULEMEDI")
        tr.koy("6", False, "tarayici=OLCULEMEDI")
        return
    tok = (v.get("onay_kutusu") == 1 and v.get("onaysiz_dugme_kapali") is True and
           v.get("durustluk") == t.get("durustluk"))
    tr.koy("5", man_ok and sunucu_ok and tok, ac + " onay_kutusu=%s dugme_kapali=%s durustluk=%d" % (
        v.get("onay_kutusu"), v.get("onaysiz_dugme_kapali"), 1 if v.get("durustluk") == t.get("durustluk") else 0))
    konsol = v.get("konsol") or []
    tr.koy("6", not v.get("hata") and v.get("secildi") and v.get("tasma") == 0 and not konsol and
           v.get("genislik") == 375,
           "genislik=%s tasma=%s konsol=%d%s%s" % (v.get("genislik"), v.get("tasma"), len(konsol),
                                                  (" hata=" + v["hata"]) if v.get("hata") else "",
                                                  (" ilk=" + konsol[0]) if konsol else ""))


def mutant_on_kosul(acik_kodlar):
    """Acik olmayan kategori -> sunucu 400. Donus (gecti, aciklama)."""
    kapali = [t["kod"] for t in MAN["turler"] if t["kod"] not in acik_kodlar]
    kod = kapali[0] if kapali else YER_TUTUCU_TUR
    k, j = post_429("/api/shop/foto/onizleme", {"tur": kod, "olcu_mm": 100, "aydinlatma_onay": True,
                                                "onay_surum": MAN["onay_surum"]})
    return k == 400, "kapali_tur=%s kod=%s hata=%s" % (kod, k, j.get("hata"))


MAN = {}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Foto ORNEK- uctan uca kabul (yalniz onizleme)")
    ap.add_argument("--tur", action="append", default=[], help="tur kodu (tekrarlanabilir)")
    ap.add_argument("--hepsi", action="store_true", help="manifestteki tum turler")
    ap.add_argument("--kol", choices=["D", "M", "R"], help="--hepsi ile: yalniz bu motor")
    a = ap.parse_args(argv)
    gecici = tempfile.mkdtemp(prefix="foto-uu-")
    try:
        MAN.clear()
        MAN.update(manifest_oku())
        harita = {t["kod"]: t for t in MAN["turler"]}
        kodlar = list(a.tur)
        if a.hepsi:
            kodlar += [k for k, t in harita.items() if not a.kol or t.get("motor") == a.kol]
        kodlar = list(dict.fromkeys(kodlar))
        if not kodlar:
            print("HATA tur yok (--tur <kod> | --hepsi [--kol D])")
            print("HAZIR=0/0 rc=2")
            return 2
        bulut = Bulut(*hedef_adlari())
        k, _, b = http("GET", taban() + "/api/shop/foto/acik")
        acik = json_coz(b) if k == 200 else {}
        if k != 200:
            raise Ayar("/foto/acik %s" % k)
        acik_kodlar = {x.get("kod") for x in acik.get("turler") or []}
        mg, mac = mutant_on_kosul(acik_kodlar)
        print("MUTANT acik-olmayan-kategori->400: %s %s" % ("KIRMIZI-YAKAR(gecerli)" if mg else "GECERSIZ", mac))
        if not mg:
            print("HAZIR=0/%d rc=2" % len(kodlar))
            return 2
        turler = [Tur(kod, harita.get(kod) or {}) for kod in kodlar]
        calisan = []
        for tr in turler:
            if not tr.t:
                for o in OLCUTLER:
                    tr.koy(o, False, "manifestte-yok")
                continue
            olc_1(tr, acik_kodlar)
            hazirla(tr)
            if tr.hazirlik:
                for o in ("2", "3", "4", "5"):
                    tr.koy(o, False, "ornek-girdi: " + tr.hazirlik)
                continue
            if tr.t.get("kol") != "deterministik":
                tr.koy("2", False, "kol=%s (saglayici kolu bu betikte OLCULMEZ — kredi)" % tr.t.get("kol"))
                tr.koy("4", False, "kol=%s OLCULEMEDI" % tr.t.get("kol"))
                calisan.append(tr)
                continue
            onizleme_isi_yaz(tr, bulut, gecici)
            calisan.append(tr)
        det = [tr for tr in calisan if tr.is_no]
        if any(not tr.t.get("tarayici_onizleyici") for tr in det):
            son, _ = kosucu_kos()
            print("KOPRU onizleme: %s" % son)
        for tr in det:
            olc_2(tr, bulut, gecici)
            if tr.s["2"][0]:
                ornek_siparis_yaz(tr, bulut)
        sip = [tr for tr in det if tr.s["2"][0]]
        if sip:
            son, _ = kosucu_kos()
            print("KOPRU siparis: %s" % son)
        for tr in det:
            if tr.s["2"][0]:
                olc_4(tr, bulut, gecici)
            else:
                tr.koy("4", False, "onizleme yok -> ORNEK siparis acilmadi")
        tar = tarayici_olc([tr.kod for tr in calisan])
        for tr in calisan:
            olc_3_5_6(tr, acik, tar)
        n = 0
        for tr in turler:
            satir = " ".join("%s%s" % (ETIKET[o], "HAZIR" if tr.s[o][0] else "EKSIK") for o in OLCUTLER)
            print("TUR %s %s => %s%s" % (tr.kod, satir, "HAZIR" if tr.hazir() else "EKSIK",
                                         (" is=%s" % tr.is_no) if tr.is_no else ""))
            for o in OLCUTLER:
                print("  %s %s %s" % (ETIKET[o], "HAZIR" if tr.s[o][0] else "EKSIK", tr.s[o][1]))
            n += 1 if tr.hazir() else 0
        rc = 0 if n == len(turler) else 1
        print("HAZIR=%d/%d rc=%d" % (n, len(turler), rc))
        return rc
    except Ayar as e:
        print("OLCULEMEDI %s" % e)
        print("HAZIR=0/%d rc=2" % len(a.tur or []))
        return 2
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
