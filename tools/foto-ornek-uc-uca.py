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
                     olcude "<mm> mm → <TL> TL" yaziyor.
                     TURETILMIS eksen (manifest olcu_ekseni): surgu YOK (S1 not var) ve
                     onizleme olcusu (olcu.json uzun kenar, yarim yukari) == D1 olcu_mm · x 1000 == sunucu
                     /foto/durum fiyat_kurus == bolumun gosterdigi "<mm> mm → <TL> TL" (S3, prova isiyle)
  (4) ORNEK siparis: odemesiz `ORNEK-<is ilk 12>` uretim satiri (kalem 0) -> kopru -> uretec -> 3MF ->
                     asama 'hazir' + panel listesi (panelOrnekListe sorgusu) kaydi; 3MF BAGIMSIZ olculur:
                     her nesne su gecirmez (her yonlu kenar tam 1 kez + tersi var) + dunya kutusunun en uzun
                     ekseni olcu_mm +-%1 + olcu.json alanlari dolu (model_sha256 == 3MF sha256)
  (5) aydinlatma   : manifest durustluk + ornek_notu + aydinlatma maddeleri dolu; sunucu onaysiz istegi 400
                     `onay-yok` ile REDDEDER, onayli istek onaya takilmaz (403 bot-dogrulama: yazim 0);
                     tarayicida aydinlatma kutusunda TEK onay kutusu + onaysiz dugme KAPALI + durustluk metni
  (6) 375 px       : mobil emulasyonda (375x812, mobile) tur secili iken yatay tasma 0 + konsol hatasi 0

MUTANT (her kosumda, olcutun on kosulu): acik OLMAYAN bir kategoriye (manifest - /acik; hepsi aciksa
manifestte OLMAYAN sabit `BILINMEYEN_TUR`) onizleme istegi -> sunucu 400 + `hata="tur-kapali"` DEMELI.
Daha gevsek esik (yalniz `kod==400`) bugun figur gercek ve ACIK ture dusup gorsel-gecersiz 400'e
kacinca KOR gecer; bekci metni KAYNAKTAN okur (`shop/src/foto.js` /foto/onizleme) — farkli 400 ya
kod 200/4xx/5xx GECERSIZ sayilir (rc 2, HAZIR=0).

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
# Manifestte OLMAYAN sabit kod — tumu ACIK oldugunda mutant on-kosulu bu kodu gonderir; sunucu bunu
# tip kapisindan (`shop/src/foto.js` /foto/onizleme `if (!tur) { return fjson({ hata: ... }, 400) }`)
# 400 ile reddetmeli. Manifeste biri yanlislikla girerse bekci kendi kendini yaralar (rc 2). Sabit
# deger `"uu-yok-tur"` (yok_tur ile biten) kasten secildi: manifest kodlari tek hece/kisa isimler.
BILINMEYEN_TUR = "uu-yok-tur"
ONIZLEME_MIN_PX = 1024
TOLERANS = {"D": 0.01, "R": 0.03, "M": 0.01}
# SAGLAYICI KOLU KREDI KAPISI (kopru-15, 8 Eki 2026). Bedeller UST SINIRDIR (shop/src/foto.js krediYaz cagri
# yerleri); gercek dusumu SUNUCU saglayici yanitindan D1 `foto_kredi`ye yazar — betik YAZMAZ, FARKI olcer.
# Onizleme sürümünde cron YOK: zincir `/yonet/foto/uretim-tik` ile tur tur ilerler; her tikten ONCE o tikte
# BASLAYABILECEK ucretli adimin bedeli kapidan gecer (build-baslat -> build; analiz -> onarim|doku|renk;
# onarim/doku -> sonraki adim). Yoklama asamalari 0: bedel adim baslarken ayrildi.
# GERCEK ZINCIR (shop/src/foto.js uretimAdimi; sira analiz->onarim->doku->analiz->renk->hazir): her
# KREDI_TIK anahtari o ASAMANIN TIKINDE BASLAYABILECEK ucretli adimin ust siniri; yoklama 0:
#   build-baslat -> build          30  (krediYaz satir 1976; uretimAdimi `build-baslat` blogu)
#   build         -> analiz          0  (1979: analizBaslat — uretimAdimi `build` blogu)
#   analiz        -> onarim|renk    10  (2006 renkBaslat VEYA 2016 onarim krediYaz; uretimAdimi `analiz`)
#   onarim        -> doku           10  (krediYaz satir 2016, doku baslatma 2030; uretimAdimi `onarim`)
#   doku          -> analiz          0  (uretim-doku bitince YenIDEN analizBaslat: 2045 — ucretsiz re-analiz)
#   renk          -> hazir           0  (krediYaz satir 2054; uretimAdimi `renk`)
# `doku` 0 cunku doku adiminin kendi ucreti zincirin oncesinde `onarim` Tikte (10) zaten ayrilmis; uretim-doku
# bittikten sonra analizBaslat yalniz bir sonraki (ucretsiz re-)analiz->renk kapisini acar.
KREDI_ONIZLEME = 6
# CESIT KOLU (TUR-C2c, --cesit figur): anahtarlik figur cesidi saglayici koluna gider (shop/src/foto.js figurKolu).
# Olcu 60 (B2, KraL 10 Eki): surgu = KULAK DAHIL en uzun boyut (cesit 60..72, olcu_en_cok 72); sunucu ciplak figuru
# olcuye olcekler, koşucu tepe sigmazsa sirta duser -> model (figur + kulak) uzun kenari = olcu ± tol. Kulak
# olcumleri koşucunun --kanit-dizin kopyasindan (figur_kulak ozet.json `kulak`) okunur; 4 alan sayi > 0 olmali.
# TUR-C2d (K2 tepe -> sirt dususu): kullanilan `konum` da ④ ekseninde (tepe|sirt; yoksa EKSIK).
FIGUR_OLCU_MM = 60
KULAK_ALANLARI = ("dis_cap_olculen_mm", "delik_cap_olculen_mm", "min_et_mm", "bag_genislik_mm")
KULAK_KONUMLARI = ("tepe", "sirt")
KREDI_TIK = {"build-baslat": 30, "analiz": 10, "onarim": 10, "doku": 0}
# KREDI_TIK_POST: her POST'tan sonra D1 farki tavan asimi KONTROLU (BETIK `ayir` sadece BIR SONRAKI adimi
# gorur; cum D1 ancak POST sonrasi yakalanir). Renk adiminin kendisi 10 ama KREDI_TIK['renk']=0; zincir
# sonunda D1 fark ile yakalanir.
KREDI_TIK_POST_TAVAN_KONTROLU = True
# DILIM TAVANI (10 Eki): --kredi-tavani KOŞUM basidir; zincir birden cok koşuma (ornek + --devam-is tekrari)
# bolunurse koşum tavani toplami tutmaz (olculdu: figur 2 x 66 = 132, tavan 70). Dilim defteri ONIZLEME D1
# `foto_kredi_dilim` (goc dosyasi asagida; betik IF NOT EXISTS ile kendisi uygular); dilim harcanan =
# SUM(foto_kredi.kredi) WHERE is_no IN (dilimin is_no'lari) + bu koşumda ayrilan (yazilmamis) ust sinir.
DILIM_GOC = os.path.join(KOK, "tools", "d1-goc", "2026-10-10-foto-kredi-dilim.sql")
DILIM_DESEN = re.compile(r"^[a-z0-9-]{3,40}$")
YOKLAMA_SAYI = 120
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
  tarayici_onizleyici:!!(F.TARAYICI_ONIZLEYICI&&F.TARAYICI_ONIZLEYICI[t.uretec]===true),
  turetilmis:F.olcuTuretilmis(t.kod),
  cesitler:(F.cesitler&&F.cesitler[t.kod])?F.cesitler[t.kod].secenekler:[]}))};
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

    def sil(self, anahtar):
        self.wr(["r2", "object", "delete", self.kova + "/" + anahtar, "--remote"])

    def al(self, anahtar, hedef):
        p = self.wr(["r2", "object", "get", self.kova + "/" + anahtar, "--remote", "--file", hedef])
        return p.returncode == 0 and os.path.isfile(hedef)


# ------------------------------------------------------------------ HTTP
def http(yontem, url, govde=None, zaman=30, baslik=None):
    """Donus (kod, baslik_tur, govde_bayt). Ag hatasi -> (0, '', b'')."""
    esle = os.environ.get("FOTO_UU_MEDYA_ESLE", "")
    if "=" in esle:
        a, b = esle.split("=", 1)
        if url.startswith(a):
            url = b + url[len(a):]
    veri = json.dumps(govde).encode() if govde is not None else None
    bas = {"User-Agent": "pruvo-ornek-uc-uca/1", "Content-Type": "application/json", "Origin": taban()}
    bas.update(baslik or {})
    r = urllib.request.Request(url, data=veri, method=yontem, headers=bas)
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


def yonet(yontem, yol, govde=None):
    """Onizleme surumunun ORNEK/tik ucu (/api/shop/yonet<yol>). Panel SIFRESI KULLANILMAZ: yalniz onizlemede ve yalniz
    bu uclarda gecerli makine anahtari (env ONIZLEME_MAKINE_ANAHTARI; shop/src/yonet.js makineAnahtariGecerli).
    Deger hicbir yere BASILMAZ; yoksa Ayar -> kosum OLCULEMEDI (kredi harcanmadan)."""
    a = os.environ.get("ONIZLEME_MAKINE_ANAHTARI", "").strip()
    if not a:
        raise Ayar("ONIZLEME_MAKINE_ANAHTARI yok")
    return http(yontem, taban() + "/api/shop/yonet" + yol, govde, zaman=120, baslik={"X-Onizleme-Makine": a})


class Kredi:
    """FAIL-CLOSED kredi kapisi (saglayici kolu). taban = kosum basi D1 `foto_kredi` toplami; harcanan =
    max(D1 farki, bu kosumda ayrilan ust sinir) — sunucu kaydi gecikse de ayrilan bedel sayilir. D1 okunamazsa
    Ayar -> kosum OLCULEMEDI (kredi harcanmadan).
    DILIM: koşum tavanina EK olarak zincir toplami (DILIM_GOC). dilim_taban = dilimin bu koşumdan ONCEKI D1
    toplami (--devam-is ile ilk kez kaydedilen is_no'nun gecmis kredisi de tabana girer)."""

    def __init__(self, bulut, tavan, dilim="", dilim_tavan=0):
        self.bulut, self.tavan, self.ayrilan = bulut, tavan, 0
        self.dilim, self.dilim_tavan = dilim, dilim_tavan
        self.taban = self.toplam()
        if self.dilim:
            with open(DILIM_GOC, encoding="utf-8") as f:
                self.bulut.sql(" ".join(s for s in f.read().splitlines() if s.strip() and not s.startswith("--")))
            self.dilim_taban = self.dilim_toplam()

    def dilim_toplam(self):
        r = self.bulut.sql("SELECT COALESCE(SUM(kredi), 0) AS n FROM foto_kredi WHERE is_no IN "
                           "(SELECT is_no FROM foto_kredi_dilim WHERE dilim = %s)" % sql_metin(self.dilim))
        return int(r[0]["n"]) if r else 0

    def dilim_harcanan(self):
        return max(self.dilim_toplam(), self.dilim_taban + self.ayrilan)

    def kaydet(self, is_no, onceki=False):
        """is_no'yu dilim defterine yazar. onceki=True (--devam-is): gecmis kredisi bu koşumun harcamasi
        DEGIL, dilim tabanidir."""
        if not self.dilim:
            return
        once = self.dilim_toplam()
        self.bulut.sql("INSERT OR IGNORE INTO foto_kredi_dilim (dilim, is_no, tarih) VALUES (%s, %s, %s)" % (
            sql_metin(self.dilim), sql_metin(is_no), sql_metin(simdi_iso())))
        if onceki:
            self.dilim_taban += self.dilim_toplam() - once

    def toplam(self):
        r = self.bulut.sql("SELECT COALESCE(SUM(kredi), 0) AS n FROM foto_kredi")
        return int(r[0]["n"]) if r else 0

    def harcanan(self):
        return max(self.toplam() - self.taban, self.ayrilan)

    def ayir(self, n):
        h = self.harcanan()
        if h + n > self.tavan:
            return False, "kredi-tavani %d+%d>%d (DUR, saglayiciya istek YOK)" % (h, n, self.tavan)
        if self.dilim:
            dh = self.dilim_harcanan()
            if dh + n > self.dilim_tavan:
                return False, "kredi-dilim-tavani %d+%d>%d (DUR, saglayiciya istek YOK)" % (dh, n, self.dilim_tavan)
        self.ayrilan = h + n
        return True, ""


def gorsel_boyut(b):
    """PNG/JPEG/WEBP baytindan (w, h); taninmazsa None (saglayici onizlemesi PNG olmayabilir)."""
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        return struct.unpack(">II", b[16:24])
    if b[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(b) and b[i] == 0xFF:
            if b[i + 1] in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return (w, h)
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
        return None
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and len(b) >= 30:
        c = b[12:16]
        if c == b"VP8X":
            return (1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little"))
        if c == b"VP8 ":
            w, h = struct.unpack("<HH", b[26:30])
            return (w & 0x3FFF, h & 0x3FFF)
        if c == b"VP8L":
            v = int.from_bytes(b[21:25], "little")
            return ((v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1)
    return None


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


def figur_foto():
    """Figur cesidi girdisi: tools/saglayici-ornek.py SENTETIK oyuncak kedi cizimi (kisi/marka/telifli gorsel YOK;
    vitrin figur orneginin girdisiyle AYNI ureteç)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("saglayici_ornek", os.path.join(KOK, "tools", "saglayici-ornek.py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.kedi_cizimi()


def olcu_sec(t):
    s = t.get("olcu_secenekleri") or []
    return s[len(s) // 2] if s else None


def _ayni(a, b):
    """JS `===` esdegeri (True == 1 Python'da esit; JS'te DEGIL)."""
    return (isinstance(a, bool) == isinstance(b, bool)) and a == b


def kosul_tamam(s, p):
    """VERI.alanAktif ile AYNI kural: `kosul` yoksa alan var; varsa her kosulun `alan`i p'de VE degeri
    `degerler` icinde olmali. Koşulu saglanmayan alan ornege GIRMEZ (gonderilirse sema-disi-parametre)."""
    k = s.get("kosul")
    if k is None:
        return True
    return isinstance(k, list) and all(
        isinstance(c, dict) and isinstance(c.get("degerler"), list) and c.get("alan") in p and
        any(_ayni(p[c["alan"]], d) for d in c["degerler"]) for c in k)


def sayi_gecerli(s, v):
    """VERI.parametreDogrula sayi kurali: aralikta + adim izgarasinda (tolerans adimin milyonda biri)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return False
    mn, mx, adim = s.get("min", 0), s.get("max", 0), s.get("adim") or 1
    k = (v - mn) / adim
    return mn <= v <= mx and abs(k - round(k)) <= 1e-6


def metin_gecerli(s, v):
    """Bos olmayan metin + `max` (karakter) ve `bayt_max` (UTF-8) tavanlari icinde. `liste:true` (K3c): 1..satir_max
    ogeli dizi, her oge ayni kurala (VERI.parametreDogrula metin dali aynasi)."""
    if s.get("liste") is True:
        return isinstance(v, list) and 1 <= len(v) <= (s.get("satir_max") or 0) and \
            all(metin_gecerli(dict(s, liste=False), x) for x in v)
    if not isinstance(v, str) or not v.strip():
        return False
    return (s.get("max") is None or len(v) <= s["max"]) and \
        (s.get("bayt_max") is None or len(v.encode("utf-8")) <= s["bayt_max"])


def ornek_parametre(t, olcu):
    """Form semasindan GECERLI ornek parametre (dogrulamayi VERI.parametreDogrula yapar). Alan sirasiyla:
    koşulu saglanmayan alan atlanir; sayi/metin alaninda kaydin `ornek`i (kopru-manifest-uret tasir) gecerliyse
    ONCE o, sonra `varsayilan` gecerliyse (aralik + adim / secenek) o, yoksa eski formul. NEDEN (kopru-15 SON3):
    min tabanli formul sehir'i bos alana (30,30), "PRUVO" yildiz tarih_saat'ini bicim disina dusuruyordu.
    Desteklenmeyen tip -> None (olcut EKSIK, sebep adiyla)."""
    p = {}
    for ad, s in (t.get("form") or {}).items():
        if not kosul_tamam(s, p):
            continue
        tip = s.get("tip")
        vs = s.get("varsayilan")
        if tip == "secim":
            ss = s.get("secenekler") or [None]
            p[ad] = vs if any(_ayni(vs, x) for x in ss) else ss[0]
        elif tip == "sayi" and sayi_gecerli(s, s.get("ornek")):
            p[ad] = s["ornek"]
        elif tip == "sayi" and sayi_gecerli(s, vs):
            p[ad] = vs
        elif tip == "sayi":
            mn, mx, adim = s.get("min", 0), s.get("max", 0), s.get("adim") or 1
            hedef = min(mx, max(mn, (olcu or mn) // 2))
            p[ad] = mn + math.floor((hedef - mn) / adim + 1e-9) * adim
            if isinstance(p[ad], float):
                p[ad] = round(p[ad], 9)
        elif tip == "metin" and metin_gecerli(s, s.get("ornek")):
            p[ad] = s["ornek"]
        elif tip == "metin":
            if s.get("zorunlu") is False:
                continue
            p[ad] = "https://pruvo3d.com" if s.get("bayt_max") else "PRUVO"
            if s.get("liste") is True:
                p[ad] = [p[ad]]
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
    """Donus {nesne, sizdirmaz_nesne, kutu:(x,y,z), uzun, parca, parca_en_uzun} — kosucudan BAGIMSIZ.
    p:path'li cok-dosyali 3MF destekler (BambuStudio Production); okunamazsa None.

    Kok model = `_rels/.rels`'in gosterdigi (yoksa `3D/3dmodel.model`). Tum `.model` girdileri (yol, id)
    anahtariyla okunur; `<component p:path=... objectid=...>` o dosyanin nesnesine cozulur (p:path yoksa ayni
    dosya). Donusum zinciri (bilesen transform × item transform) AYNEN uygulanir; `build`/`item` YALNIZ
    kok modelden okunur. Tek-dosya 3MF'lerde sonuc bayt bayt AYNI."""
    try:
        with zipfile.ZipFile(yol) as z:
            adlar = z.namelist()
            kok_yol = "3D/3dmodel.model"
            if "_rels/.rels" in adlar:
                rels = z.read("_rels/.rels").decode("utf-8")
                mt = re.search(r'Target="([^"]+)"\s+Id="[^"]+"\s+Type="[^"]*3dmodel"', rels)
                if mt:
                    t = mt.group(1)
                    kok_yol = t[1:] if t.startswith("/") else t
            nesne = {}
            for ad in adlar:
                if not ad.endswith(".model"):
                    continue
                try:
                    xml = z.read(ad).decode("utf-8")
                except UnicodeDecodeError:
                    continue
                for m in re.finditer(r"<object\b([^>]*)>(.*?)</object>", xml, re.S):
                    attrs, body = m.group(1), m.group(2)
                    oid_m = re.search(r'\bid="(\d+)"', attrs)
                    if not oid_m:
                        continue
                    oid = oid_m.group(1)
                    vs = [tuple(round(float(c), 4) for c in v) for v in re.findall(
                        r'<vertex\s+x="([-0-9.eE+]+)"\s+y="([-0-9.eE+]+)"\s+z="([-0-9.eE+]+)"', body)]
                    ts = [tuple(int(c) for c in t) for t in re.findall(
                        r'<triangle\s+v1="(\d+)"\s+v2="(\d+)"\s+v3="(\d+)"', body)]
                    komp = []
                    for cm in re.finditer(r'<component\b([^>]*?)(?:/>|>\s*</component>)', body):
                        c_attrs = cm.group(1)
                        oid2 = re.search(r'objectid="(\d+)"', c_attrs)
                        if not oid2:
                            continue
                        pyol_m = re.search(r'p:path="([^"]+)"', c_attrs)
                        tr_m = re.search(r'transform="([^"]+)"', c_attrs)
                        komp.append((oid2.group(1),
                                     (pyol_m.group(1) if pyol_m else ""),
                                     (tr_m.group(1) if tr_m else "")))
                    nesne[(ad, oid)] = (vs, ts, komp)
            try:
                kok_xml = z.read(kok_yol).decode("utf-8")
            except KeyError:
                return None
    except (OSError, KeyError, IndexError, zipfile.BadZipFile, UnicodeDecodeError):
        return None

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

    def yol_coz(ana_yol, yol_ifade):
        """p:path yoksa -> ana_dosya; varsa -> p:path (basinda "/" varsa kaldirilir)."""
        if not yol_ifade:
            return ana_yol
        return yol_ifade[1:] if yol_ifade.startswith("/") else yol_ifade

    def noktalar(anahtar, t, d=0):
        if anahtar not in nesne or d > 8:
            return []
        vs, _, komp = nesne[anahtar]
        ana_dosya = anahtar[0]
        out = list(vs)
        for cid, pyol, ct in komp:
            hedef = yol_coz(ana_dosya, pyol)
            out += noktalar((hedef, cid), ct, d + 1)
        return [donustur(p, t) for p in out]

    agli = [k for k, (vs, ts, _) in nesne.items() if ts]
    mn, mx = [float("inf")] * 3, [float("-inf")] * 3
    parca = []  # her build ogesinin kendi dunya kutusu (tabla duzeninde parca = urunun bir parcasi)
    for b in re.finditer(r'<item\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', kok_xml):
        anahtar = (kok_yol, b.group(1))
        if anahtar not in nesne:
            continue
        pm, px = [float("inf")] * 3, [float("-inf")] * 3
        for p in noktalar(anahtar, b.group(2)):
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
                # text yalniz "Uncaught" der; teshis icin istisnanin aciklamasi + kaynak satiri da basilir.
                d = p.get("exceptionDetails") or {}
                ac = str((d.get("exception") or {}).get("description") or "").split("\n")[0]
                n.append("istisna: %s %s @%s:%s" % (d.get("text", ""), ac, str(d.get("url") or "").rsplit("/", 1)[-1],
                                                   d.get("lineNumber")))
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
  // sayfa-3adim K3 (Okan 9 Eki 01:0x/01:4x): tek kutu 4 pencere; tur secimi = ① KARTLAR'daki kart
  // (button.foto-uretim-kart[data-tur]; figur iki kartta — insan/hayvan_model — ilki secilir). Lightbox YOK.
  let kart = null;
  for (let i = 0; i < 60; i++) {
    kart = document.querySelector('#fotoUretim button.foto-uretim-kart[data-tur="' + kod + '"]');
    if (kart) break;
    await bekle(250);
  }
  if (!kart) return {hata: 'tur-secilemiyor'};
  kart.click(); await bekle(300);
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
  const sk = document.querySelector('#fotoUretim button.foto-uretim-kart.secili');
  const a2 = document.getElementById('foto-pencere-2');
  const olculen_not = !!document.querySelector('#fotoUretim .foto-uretim-olculen-not');
  const secili = sk ? (sk.getAttribute('data-tur') || '') : '';
  return {secildi: secili === kod && !!a2 && !a2.hidden, secili_tur: secili, surgu: !!surgu, fiyat: fiyat, onay_kutusu: kutu,
          olculen_not: olculen_not,
          onaysiz_dugme_kapali: !!btn && btn.disabled === true, durustluk: dp ? dp.textContent : '',
          tasma: Math.max(d.scrollWidth - d.clientWidth, document.body.scrollWidth - d.clientWidth),
          genislik: d.clientWidth};
})()
"""


# TURETILMIS ③ (S3): prova isi oturum deposuna yazilir, sayfa yenilenir -> bolum durumu sorar ve S3'te
# onizleme olcusunun fiyatini yazar (surgu YOK).
TARAYICI_S3_JS = r"""
(async () => {
  const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
  let y = null;
  for (let i = 0; i < 80; i++) {
    y = document.querySelector('#fotoUretim .foto-uretim-olculen-fiyat');
    if (y) break;
    await bekle(250);
  }
  return {olculen_fiyat: y ? y.textContent : '', s3_surgu: !!document.getElementById('foto-olcu-s3')};
})()
"""


def tarayici_olc(kodlar, prova=None):
    """{kod: sonuc dict | {'hata': ...}}. Chrome yoksa {} (olcutler OLCULEMEDI). prova: {kod: ss kaydi}
    (TURETILMIS ③: S3 olcusu + fiyat yazisi ayni sekmede okunur)."""
    prova = prova or {}
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
                if kod in prova:
                    c.js("sessionStorage.setItem('pruvo_foto_is', %s); 1" % json.dumps(json.dumps(prova[kod])))
                    c.gonder("Page.reload")
                    time.sleep(0.5)
                    for _ in range(80):
                        if c.js("document.readyState") == "complete":
                            break
                        time.sleep(0.25)
                    v.update(c.js(TARAYICI_S3_JS) or {"s3_hata": "js-sonuc-yok"})
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
def kosucu_kos(kanit=""):
    """kanit: koşucu --kanit-dizin (figur cesidi; onarim kolunun ozet.json + onizleme.png kopyasi)."""
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
        p = subprocess.run([sys.executable, yol, "--hedef", "onizleme", "--uygula"] +
                           (["--kanit-dizin", kanit] if kanit else []), capture_output=True, text=True,
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
        self.cesit, self.cesit_tavan, self.kanit = "", None, ""

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


def cesit_kur(tr, cesit, gecici):
    """--cesit: turun cesit kaydi (VERI.cesitler) -> saglayici kolu; olcu FIGUR_OLCU_MM, parametre YOK, girdi foto
    (istemci figurde ③ formunu gizler, secim.cesit gonderir). Donus "" ya da hazirlik sebebi."""
    ck = next((c for c in tr.t.get("cesitler") or [] if c.get("kod") == cesit), None)
    if not ck or not ck.get("saglayici_tur") or not isinstance(ck.get("olcu_en_cok"), int):
        return "cesit-kaydi-yok:%s" % cesit
    if FIGUR_OLCU_MM not in (tr.t.get("olcu_secenekleri") or []) or FIGUR_OLCU_MM > ck["olcu_en_cok"]:
        return "cesit-olcu:%d" % FIGUR_OLCU_MM
    tr.cesit, tr.cesit_tavan, tr.kanit = cesit, ck["olcu_en_cok"], os.path.join(gecici, "kanit")
    tr.t = dict(tr.t, kol="saglayici")
    tr.olcu, tr.parametre, tr.secim = FIGUR_OLCU_MM, {}, {"cesit": cesit}
    tr.dosyalar = {"foto": ("foto.png", figur_foto(), "image/png")}
    return ""


def kulak_oku(yol):
    """figur_kulak ozet.json `kulak` -> {alan: deger} (KULAK_ALANLARI + konum); dosya/alan yoksa None deger."""
    try:
        with open(yol, encoding="utf-8") as f:
            oz = json.load(f)
    except (OSError, ValueError):
        oz = {}
    k = oz.get("kulak") if isinstance(oz, dict) and isinstance(oz.get("kulak"), dict) else {}
    return dict({a: k.get(a) for a in KULAK_ALANLARI}, konum=k.get("konum"))


def kulak_gecerli(kd):
    if kd.get("konum") not in KULAK_KONUMLARI:
        return False
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
               for a, v in kd.items() if a in KULAK_ALANLARI) and all(a in kd for a in KULAK_ALANLARI)


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
    # TURETILMIS eksen: musteri ucu gibi olcu 0 yazilir (surgu yok); koşucu OLCULEN degeri satira yazar.
    ist = 0 if t.get("turetilmis") else tr.olcu
    girdi = {"sozlesme": 1, "kategori": tr.kod, "siparis_no": "", "kalem": 0, "olcu_mm": ist,
             "renkler": renk, "malzemeler": malz, "parametreler": tr.parametre, "dosyalar": beyan}
    yol = os.path.join(gecici, tr.is_no + "-girdi.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(girdi, f, ensure_ascii=False)
    bulut.koy("foto-uretec-onizleme/%s/girdi.json" % tr.is_no, yol, "application/json")
    bulut.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol, hata, %s)"
              " VALUES (%s, %s, %d, %s, %s, 'uretec-onizleme', 0, '', %s)" % (
                  onay[0], sql_metin(tr.is_no), sql_metin(tr.kod), ist, sql_metin(ORNEK_ZIYARETCI),
                  sql_metin(simdi), onay[1]))


def olc_2(tr, bulut, gecici):
    t = tr.t
    r = bulut.sql("SELECT asama, hata, olcu_mm FROM foto_isler WHERE is_no = %s" % sql_metin(tr.is_no))
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
    ek = ""
    if t.get("turetilmis") and r:
        # Olcu = koşucunun D1'e yazdigi KAYIT (siparis/ORNEK bunu kullanir); uk = olcu.json (③ karsilastirir).
        tr.olcu, tr.uk, tr.dosya_png, tr.dosya_olcu = r[0].get("olcu_mm"), olcu.get("uzun_kenar_mm"), oy, jy
        ek = " olcu_mm(D1)=%s uk=%s" % (tr.olcu, tr.uk)
    tr.koy("2", ok, "asama=%s hata=%s onizleme_px=%s olcu.json=%d%s" % (
        asama, (r[0].get("hata") if r else "") or "-", "%dx%d" % b if b else "yok", 1 if olcu else 0, ek))


def ornek_siparis_yaz(tr, bulut):
    simdi = simdi_iso()
    no = ORNEK_SIPARIS_ONEK + tr.is_no[:12]
    # Olcu ISTEMCIDEN (betikten) DEGIL: onizleme isinin KAYITLI olcusu (sunucu siparis kolu ile ayni ilke).
    bulut.sql("INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel,"
              " onay_tarih, onay_surum) SELECT %s, 0, is_no, tur, olcu_mm, 'uretec-bekliyor', %s, %s, %s, %s"
              " FROM foto_isler WHERE is_no = %s" % (
                  sql_metin(no), sql_metin(simdi), sql_metin(simdi), sql_metin(simdi), sql_metin(MAN["onay_surum"]),
                  sql_metin(tr.is_no)))


def yokla_bekle():
    time.sleep(float(os.environ.get("FOTO_UU_YOKLA_SN", "5")))


def saglayici_2(tr, kredi, devam_is_no=""):
    """② SAGLAYICI: panel ornek ucu (musteri ucuyla AYNI saglayici cagrisi, shop/src/foto.js panelOrnekOnizleme)
    -> ornek-durum yoklamasi (sunucu saglayiciyi bu yoklamayla ilerletir) -> onizleme gorseli px.
    --devam-is: onizleme islemi POSPUUNA YENIDEN acilmaz (bedel onceki kosumda odendi); sadece
    tr.is_no = <is_no> ile ornek-durum + ornek-gorsel aynen (ornek-onizleme POST'U YAPMAZ, KREDI_ONIZLEME
    AYIRMAZ)."""
    if devam_is_no:
        tr.is_no = devam_is_no
    else:
        ok, sebep = kredi.ayir(KREDI_ONIZLEME)
        if not ok:
            tr.koy("2", False, sebep)
            tr.koy("4", False, sebep)
            return
        _, bayt, tip = tr.dosyalar["foto"]
        govde = {"tur": tr.kod, "olcu_mm": tr.olcu, "gorsel": "data:%s;base64,%s" % (
            tip, base64.b64encode(bayt).decode())}
        if tr.cesit:
            govde["cesit"] = tr.cesit
        k, _, b = yonet("POST", "/foto/ornek-onizleme", govde)
        j = json_coz(b)
        if k != 200 or not isinstance(j.get("is"), str):
            tr.koy("2", False, "ornek-onizleme kod=%s hata=%s" % (k, j.get("hata")))
            return
        tr.is_no = j["is"]
        # Kosum yarida kesilirse (oturum/zaman tavani) zincir --devam-is <is> ile surer: is_no HEMEN basilir.
        print("ORNEK_IS tur=%s is=%s (devam: --devam-is %s)" % (tr.kod, tr.is_no, tr.is_no), flush=True)
    # DILIM defteri: yeni is (POST) bu koşumun harcamasi; --devam-is'in gecmis kredisi dilim TABANI.
    kredi.kaydet(tr.is_no, onceki=bool(devam_is_no))
    d = {}
    for _ in range(YOKLAMA_SAYI):
        k, _, b = yonet("GET", "/foto/ornek-durum?is=" + tr.is_no)
        d = json_coz(b) if k == 200 else {}
        if d.get("asama") in ("hazir", "basarisiz", "yok"):
            break
        yokla_bekle()
    boyut = None
    if d.get("asama") == "hazir":
        k, tip, b = yonet("GET", "/foto/ornek-gorsel?is=" + tr.is_no)
        boyut = gorsel_boyut(b) if k == 200 and tip.startswith("image/") else None
    tr.koy("2", bool(boyut) and max(boyut) >= ONIZLEME_MIN_PX, "kol=saglayici asama=%s hata=%s onizleme_px=%s" % (
        d.get("asama", "yok"), d.get("hata") or "-", "%dx%d" % boyut if boyut else "yok"))


def saglayici_4(tr, kredi):
    """④ SAGLAYICI uretim: panel ornek-uret -> foto_uretim ORNEK satiri ('build-baslat') -> onizleme surumunde cron
    YOK: /yonet/foto/uretim-tik zinciri tur tur ilerletir. Her ASAMA ilk goruldugunde o tikte baslayabilecek ucretli
    adimin bedeli kredi kapisindan gecer. Tik kuyruktaki HER satiri ilerletir -> baska yarim satir varsa DUR (kendi
    satirimiz disinda kredi yakilmaz). Donus: True = zincir bitti (olc_4 olcer)."""
    k, _, b = yonet("POST", "/foto/ornek-uret", {"is": tr.is_no})
    j = json_coz(b)
    if k != 200 or not j.get("siparis_no"):
        tr.koy("4", False, "ornek-uret kod=%s hata=%s" % (k, j.get("hata")))
        return False
    no, onceki, onarim_kosu = j["siparis_no"], None, 0
    for _ in range(YOKLAMA_SAYI):
        r = kredi.bulut.sql("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = %s AND kalem = 0" % sql_metin(no))
        asama = r[0]["asama"] if r else "yok"
        if asama in ("hazir", "elle", "yok"):
            if asama != "hazir":
                tr.koy("4", False, "siparis=%s asama=%s sebep=%s" % (no, asama, (r[0]["sebep"] if r else "") or "-"))
            return asama == "hazir"
        # ONARIM KAPISI (8 Eki): saglayici zinciri 'onarim-bekliyor'da biter; 'hazir'i yalniz yerel kosucunun
        # onarim kuyrugu yazar (TeKiN koprusu + --olc). Onizlemede launchd yok -> kosucu burada BIR kez kosar
        # (kredi 0, saglayiciya istek yok). Kosum sonrasi hala bekliyorsa (kopru yok / erisim) DUR.
        if asama == "onarim-bekliyor":
            if onarim_kosu:
                tr.koy("4", False, "siparis=%s onarim-bekliyor kosucu sonrasi da (%s)" % (no, onarim_son))
                return False
            onarim_kosu, (onarim_son, _) = 1, kosucu_kos(tr.kanit)
            print("KOPRU onarim: %s" % onarim_son)
            continue
        y = kredi.bulut.sql("SELECT COUNT(*) AS n FROM foto_uretim WHERE asama NOT IN ('hazir', 'elle', "
                            "'uretec-bekliyor', 'onarim-bekliyor') AND siparis_no != %s" % sql_metin(no))
        if y and y[0]["n"]:
            tr.koy("4", False, "yabanci-kuyruk=%d (tik onlari da ilerletir; kredi yakilmaz, DUR)" % y[0]["n"])
            return False
        if asama != onceki:
            print("ASAMA siparis=%s asama=%s rezerv=%d" % (no, asama, kredi.ayrilan), flush=True)
            ok, sebep = kredi.ayir(KREDI_TIK.get(asama, 0))
            if not ok:
                tr.koy("4", False, "siparis=%s asama=%s %s" % (no, asama, sebep))
                return False
            onceki = asama
        k, _, _ = yonet("POST", "/foto/uretim-tik", {})
        if k != 200:
            tr.koy("4", False, "uretim-tik kod=%s" % k)
            return False
        # POST sonrasi D1 fark tavan kontrolu: BETIK `ayir` (Tik basinda) yalniz BIR SONRAKI adimi gorur;
        # cum D1 (ornek doku->renk gecisi) yalniz POST sonrasi yakalanir. Renk gibi KREDI_TIK=0 adimlar
        # icin gec yakalama olmadan kullanici tasarini gormezden gelir.
        if KREDI_TIK_POST_TAVAN_KONTROLU:
            h = kredi.toplam() - kredi.taban
            if h > kredi.tavan:
                tr.koy("4", False, "kredi-tavani D1 %d>%d (POST sonrasi, renk oncesi DUR)" % (h, kredi.tavan))
                return False
            if kredi.dilim:
                dh = kredi.dilim_toplam()
                if dh > kredi.dilim_tavan:
                    tr.koy("4", False, "kredi-dilim-tavani D1 %d>%d (POST sonrasi, renk oncesi DUR)" % (
                        dh, kredi.dilim_tavan))
                    return False
        yokla_bekle()
    tr.koy("4", False, "siparis=%s zaman-asimi asama=%s" % (no, onceki))
    return False


def glb_gecerli(yol):
    try:
        with open(yol, "rb") as f:
            b = f.read(12)
    except OSError:
        return False
    return len(b) == 12 and b[:4] == b"glTF"


PROVA_ZIYARETCI = "uu-prova"


def prova_kur(tr, bulut):
    """TURETILMIS ③: ORNEK isi musteri ucunda gorunmez (durum 404) -> onizlemenin MUSTERI kopyasi (ayni
    onizleme.png + olcu.json, olcu_mm KAYITTAN) acilir; sunucu fiyati /foto/durum'dan okunur. prova_sil siler."""
    tr.prova = secrets.token_hex(16)
    for ad, yol, tip in (("onizleme.png", tr.dosya_png, "image/png"), ("olcu.json", tr.dosya_olcu, "application/json")):
        bulut.koy("foto-uretec-onizleme/%s/%s" % (tr.prova, ad), yol, tip)
    simdi = simdi_iso()
    bulut.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, son_kontrol, hata,"
              " onay_tarih, onay_surum) SELECT %s, tur, olcu_mm, %s, %s, 'onizleme-hazir', %s, 0, '', %s, %s"
              " FROM foto_isler WHERE is_no = %s" % (
                  sql_metin(tr.prova), sql_metin(PROVA_ZIYARETCI), sql_metin(simdi), sql_metin(simdi),
                  sql_metin(simdi), sql_metin(MAN["onay_surum"]), sql_metin(tr.is_no)))
    k, _, b = http("GET", taban() + "/api/shop/foto/durum?is=" + tr.prova)
    tr.durum = json_coz(b) if k == 200 else {"kod": k}


def prova_sil(tr, bulut):
    if not getattr(tr, "prova", ""):
        return
    bulut.sql("DELETE FROM foto_isler WHERE is_no = %s AND ziyaretci = %s" % (sql_metin(tr.prova),
                                                                           sql_metin(PROVA_ZIYARETCI)))
    for ad in ("onizleme.png", "olcu.json"):
        bulut.sil("foto-uretec-onizleme/%s/%s" % (tr.prova, ad))


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
    # SAGLAYICI zinciri (renk asamasi) model.3mf + model.glb yazar; olcu.json/onizleme.png YOK (olcek kapisi
    # sunucuda ucmfOlcekle). Geometri olcumu ikisinde de AYNI (bagimsiz 3MF olcumu, asagida).
    sag = tr.t.get("kol") == "saglayici"
    adlar = ("model.3mf", "model.glb") if sag else ("model.3mf", "olcu.json", "onizleme.png")
    dosya = {ad: os.path.join(d, ad) for ad in adlar}
    var = k.get("asama") == "hazir" and all(bulut.al("foto/%s/0/%s" % (no, ad), y) for ad, y in dosya.items())
    if not var:
        tr.koy("4", False, "siparis=%s asama=%s sebep=%s dosya=yok" % (no, k.get("asama"), k.get("sebep") or "-"))
        if tr.t.get("tarayici_onizleyici"):
            tr.koy("2", False, tr.s["2"][1] + " · uretec onizlemesi YOK")
        return
    try:
        olcu = {} if sag else json.load(open(dosya["olcu.json"], encoding="utf-8"))
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
    if tr.cesit:
        # CESIT KOLU: model = figur + kulak (figur_kulak) -> olcek ekseni KULAK DAHIL uzun kenar = olcu ± tol
        # (B2: surgu kulak dahil; olcu cesit tavanini asamaz).
        eksen_yolu = "cesit-kulak-dahil=%d" % tr.olcu
        eksen = bool(m) and tr.olcu <= tr.cesit_tavan and abs(m["uzun"] - tr.olcu) <= tr.olcu * tol + 1e-9
    elif m and not eksen and m["parca"] > 1 and m["uzun"] > tr.olcu:
        eksen_yolu = "montaj"
        eksen = (m["parca_en_uzun"] <= tr.olcu * (1 + tol) + 1e-9 and isinstance(uk, (int, float)) and
                 abs(uk - tr.olcu) <= tr.olcu * tol + 1e-9)
    alanlar = (olcu.get("sozlesme") == 1 and olcu.get("kategori") == tr.kod and isinstance(uk, (int, float)) and
               abs(uk - tr.olcu) <= tr.olcu * tol + 1e-9 and olcu.get("sizdirmaz") is True and
               isinstance(olcu.get("renk_sayisi"), int) and 1 <= olcu["renk_sayisi"] <= 4 and
               all((olcu.get("kutu_mm") or {}).get(e, 0) > 0 for e in "xyz") and olcu.get("model_sha256") == msha)
    if sag:
        # olcu.json sozlesmesi saglayici kolunda yok: alan = GLB gecerli; onizleme = ②'nin saglayici gorseli.
        alanlar, b = glb_gecerli(dosya["model.glb"]), None
        pv = tr.s["2"][0]
        if tr.cesit:
            # Koşucu --kanit-dizin: figur_kulak ozet.json (kulak 4 sayi) + onizleme.png (koşucu §3 donusumu).
            kd = os.path.join(tr.kanit, no)
            tr.kulak = kulak_oku(os.path.join(kd, "ozet.json"))
            b = png_boyut(os.path.join(kd, "onizleme.png")) if os.path.isfile(os.path.join(kd, "onizleme.png")) else None
            alanlar = alanlar and kulak_gecerli(tr.kulak) and bool(b)
            tr.dosya_yollari = {"model.3mf": dosya["model.3mf"], "ozet.json": os.path.join(kd, "ozet.json"),
                                "onizleme.png": os.path.join(kd, "onizleme.png")}
    else:
        b = png_boyut(dosya["onizleme.png"])
        pv = bool(b) and max(b) >= ONIZLEME_MIN_PX
    tr.koy("4", kayit and sizd and eksen and alanlar and pv,
           "siparis=%s kayit=%d sizdirmaz=%s/%s kutu=%s uzun=%s eksen=%s parca=%s parca_en_uzun=%s hedef=%d±%g%% "
           "olcu.json_uzun=%s alanlar=%d onizleme=%s" % (
               no, 1 if kayit else 0, m["sizdirmaz_nesne"] if m else 0, m["nesne"] if m else 0,
               m["kutu"] if m else None, m["uzun"] if m else None, eksen_yolu if eksen else "YANLIS",
               m["parca"] if m else 0, m["parca_en_uzun"] if m else None, tr.olcu, tol * 100, uk,
               1 if alanlar else 0, "%dx%d" % b if b else "yok") +
           ((" kulak=%s" % json.dumps(tr.kulak, sort_keys=True)) if tr.cesit else ""))
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
    g["secim"] = tr.secim   # cesit kolunda {"cesit": ...} (istemci govde.secim.cesit, TUR-C2b)
    if "foto" in tr.dosyalar:
        g["gorsel"] = "data:image/png;base64," + base64.b64encode(tr.dosyalar["foto"][1]).decode()
    if "svg" in tr.dosyalar:
        g["svg"] = tr.dosyalar["svg"][1].decode()
    return "/api/shop/foto/onizleme", g


# Fiyat beklentisi BAGIMSIZ carpim (VERI'den okunmaz): max(600 TL, mm × 10 TL) — Okan 8 Eki tabani.
TABAN_KURUS = 60000


def beklenen_kurus(mm):
    return max(mm * 1000, TABAN_KURUS)


def fiyat_yazisi(mm):
    return "%d mm → %s TL" % (mm, "{:,}".format(beklenen_kurus(mm) // 100).replace(",", "."))


def olc_3_turetilmis(tr, a, v):
    """TURETILMIS eksen: max(600 TL, onizleme olcusu x 10 TL) == sunucu fiyati (durum) == bolumun S3 yazisi; surgu YOK."""
    t = tr.t
    uk = getattr(tr, "uk", None)
    olculen = int(math.floor(uk + 0.5)) if isinstance(uk, (int, float)) and not isinstance(uk, bool) and uk > 0 else None
    bek = beklenen_kurus(olculen) if olculen else None
    sunucu = (getattr(tr, "durum", None) or {}).get("fiyat_kurus")
    kaynak = (getattr(tr, "durum", None) or {}).get("olcu_kaynagi")
    yazi = fiyat_yazisi(olculen) if olculen else None
    api_ok = a is not None and t.get("formul") == "mm_x_10tl" and t.get("formul_kurus_mm") == 1000
    gos = (v or {}).get("olculen_fiyat")
    esit = bek is not None and tr.olcu == olculen and sunucu == bek and gos == yazi
    if not v:
        tr.koy("3", False, "api=%d onizleme_olcu=%s sunucu=%s tarayici=OLCULEMEDI" % (1 if api_ok else 0, olculen, sunucu))
        return
    surgusuz = not v.get("surgu") and v.get("olculen_not") is True and v.get("s3_surgu") is False
    tr.koy("3", api_ok and esit and surgusuz and kaynak == "turetilmis",
           "api=%d uk=%s onizleme_olcu=%s D1=%s beklenen_kurus=%s sunucu_kurus=%s kaynak=%s gosterilen=%r beklenen=%r "
           "surgu=%d not=%d s3_surgu=%s" % (
               1 if api_ok else 0, uk, olculen, tr.olcu, bek, sunucu, kaynak, gos, yazi, 1 if v.get("surgu") else 0,
               1 if v.get("olculen_not") else 0, v.get("s3_surgu")))


def olc_3_5_6(tr, acik, tar):
    t = tr.t
    # (3) API: /acik olculeri == olcuSecenekleri ve fiyat == max(taban, mm x formul) (bagimsiz carpim).
    a = next((x for x in (acik.get("turler") or []) if x.get("kod") == tr.kod), None)
    beklenen = t.get("olcu_secenekleri") or []
    api_ok = (a is not None and t.get("formul") == "mm_x_10tl" and t.get("formul_kurus_mm") == 1000 and
              [o.get("mm") for o in a.get("olculer") or []] == beklenen and beklenen and
              all(o.get("fiyat_kurus") == beklenen_kurus(o.get("mm")) for o in a.get("olculer") or []) and
              all(k == beklenen_kurus(mm) for mm, k, _ in t.get("fiyatlar") or []))
    v = tar.get(tr.kod) if tar else None
    if v is not None and not v.get("secildi"):
        # Tur tarayicida SECILEMIYORSA (3)(5)(6) baska turun sayfasini olcerdi -> hepsi EKSIK, sebep adiyla.
        v = dict(v, surgu=False, onay_kutusu=0, hata=v.get("hata") or "secili_tur=%r" % v.get("secili_tur"))
    uc = beklenen[-1] if beklenen else 0
    beklenen_yazi = fiyat_yazisi(uc)
    if t.get("turetilmis"):
        olc_3_turetilmis(tr, a, v)
    elif not v:
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


def _red_metni_onizleme():
    """shop/src/foto.js `onizlemeUcu` fonksiyonu icindeki `if (!tur) { return fjson({ hata: "X" }, 400) }`
    — X. Kaynaktan okunur; ikinci bir sabit sozluk UYDURULMAZ. Bulunamazsa Ayar (kapali yol)."""
    import re as _re
    src = open(os.path.join(SHOP, "src", "foto.js"), encoding="utf-8").read()
    m = _re.search(r'async\s+function\s+onizlemeUcu\s*\([^)]*\)\s*\{', src)
    if not m:
        raise Ayar("shop/src/foto.js: onizlemeUcu fonksiyonu bulunamadi (bekci yazisi kaynaktan okunamadi)")
    sonraki = _re.search(r'(?:export\s+)?async\s+function\s+\w+\s*\([^)]*\)\s*\{', src[m.end():])
    govde = src[m.end(): m.end() + sonraki.start()] if sonraki else src[m.end():]
    rm = _re.search(r'if\s*\(\s*!\s*tur\s*\)\s*\{\s*return\s+fjson\(\s*\{\s*hata:\s*"([^"]+)"\s*\}\s*,\s*400\s*\)',
                    govde)
    if not rm:
        raise Ayar("shop/src/foto.js: onizlemeUcu /foto/onizleme tur-red metni bulunamadi")
    return rm.group(1)


def mutant_on_kosul(acik_kodlar):
    """Acik olmayan kategori -> sunucu 400 + TURE-RED metni. Donus (gecti, aciklama).

    Kapali tur varsa onu deneriz; yoksa manifestte OLMAYAN sabit `BILINMEYEN_TUR` ile deneriz (URETEC
    her durumda sunucudan `shop/src/foto.js` /foto/onizleme tip kapisinin reddini bekler). Yalniz
    `kod == 400` yetmez — reddin `hata` metni `tur-kapali` (kaynaktan okunan) OLMALI; aksi (ornek
    bugun figur acilip gorsel-gecersiz 400'e dusmesi) sunucu KAPI KAPALI degil demektir, GECERSIZ."""
    hata_bek = _red_metni_onizleme()
    # Yalniz SAGLAYICI kolu (motor M) kapali turu: D/R kolundaki kapali tur /foto/onizleme'de once
    # turHazir'a takilir ve 503 `kapali` doner (9 Eki 2026 olcumu: anahtarlik kaydi geldi, ornegi yok) —
    # o da fail-closed ama bu bekcinin olctugu `tur-kapali` dali DEGIL; o kod BILINMEYEN_TUR'a duser.
    kapali = [t["kod"] for t in MAN["turler"] if t["kod"] not in acik_kodlar and t.get("motor") == "M"]
    if kapali:
        kod = kapali[0]
        kaynak = "kapali"
    else:
        if any(t["kod"] == BILINMEYEN_TUR for t in MAN["turler"]):
            return False, ("BILINMEYEN_TUR=%s manifestte BULUNDU — bekciyi devre disi birakma; "
                           "kaldir yeni sabit sec (beklenen kod=%s, hata=%s)" %
                           (BILINMEYEN_TUR, 400, hata_bek))
        kod = BILINMEYEN_TUR
        kaynak = "yok_tur"
    k, j = post_429("/api/shop/foto/onizleme", {"tur": kod, "olcu_mm": 100, "aydinlatma_onay": True,
                                                "onay_surum": MAN["onay_surum"]})
    return k == 400 and j.get("hata") == hata_bek, (
        "%s=%s kod=%s hata=%s bek_kod=%s bek_hata=%s" % (kaynak, kod, k, j.get("hata"), 400, hata_bek))


MAN = {}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Foto ORNEK- uctan uca kabul (yalniz onizleme)")
    ap.add_argument("--tur", action="append", default=[], help="tur kodu (tekrarlanabilir)")
    ap.add_argument("--hepsi", action="store_true", help="manifestteki tum turler")
    ap.add_argument("--kol", choices=["D", "M", "R"], help="--hepsi ile: yalniz bu motor")
    ap.add_argument("--kredi-tavani", type=int, default=0,
                    help="saglayici kolu: bu kosumda harcanabilecek kredi (0 = saglayiciya istek YOK, ②④ OLCULMEZ)")
    ap.add_argument("--dilim", default="",
                    help="saglayici kolu: zincir/dilim etiketi (^[a-z0-9-]{3,40}$); tavan ZINCIR TOPLAMIDIR (ornek + "
                         "--devam-is tekrari dahil, ONIZLEME D1 foto_kredi_dilim). --kredi-tavani > 0 iken ZORUNLU.")
    ap.add_argument("--dilim-tavan", type=int, default=0,
                    help="dilimin TOPLAM kredi tavani (onceki koşumlar dahil). --kredi-tavani > 0 iken ZORUNLU (> 0).")
    ap.add_argument("--cesit", choices=["figur"], default="",
                    help="tur cesidi (VERI.cesitler; anahtarlik figur -> saglayici kolu). Yalniz TEK --tur ve "
                         "--kredi-tavani > 0 ile gecerli.")
    ap.add_argument("--cikti-dizin", default="",
                    help="cesit kolu: ④'un model.3mf + ozet.json + onizleme.png kopyasi bu dizine (rapor icin)")
    ap.add_argument("--devam-is", default="",
                    help="saglayici kolu: onceki kosumda park etmis is_no'dan zinciri surdurur "
                         "(ornek-onizleme POST'U YAPMAZ, KREDI_ONIZLEME ayirmaz). Yalniz --kredi-tavani > 0 "
                         "ve TEK --tur ile gecerli; --hepsi ile birlikte kullanilamaz.")
    a = ap.parse_args(argv)
    if a.kredi_tavani > 0 and (not DILIM_DESEN.match(a.dilim or "") or a.dilim_tavan <= 0):
        print("HATA dilim: --kredi-tavani > 0 iken --dilim <^[a-z0-9-]{3,40}$> ve --dilim-tavan <N > 0> ZORUNLU "
              "(dilim=%r dilim-tavan=%d; saglayiciya istek YOK)" % (a.dilim, a.dilim_tavan))
        print("HAZIR=0/0 rc=2")
        return 2
    if a.devam_is and (a.kredi_tavani <= 0 or len(a.tur) != 1 or a.hepsi):
        print("HATA --devam-is yalniz --kredi-tavani > 0 ve TEK --tur ile gecerli")
        print("HAZIR=0/0 rc=2")
        return 2
    if a.cesit and (a.kredi_tavani <= 0 or len(a.tur) != 1 or a.hepsi):
        print("HATA --cesit yalniz --kredi-tavani > 0 ve TEK --tur ile gecerli")
        print("HAZIR=0/0 rc=2")
        return 2
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
        calisan, sag = [], []
        for tr in turler:
            if not tr.t:
                for o in OLCUTLER:
                    tr.koy(o, False, "manifestte-yok")
                continue
            olc_1(tr, acik_kodlar)
            hazirla(tr)
            if a.cesit and not tr.hazirlik:
                tr.hazirlik = cesit_kur(tr, a.cesit, gecici)
            if tr.hazirlik:
                for o in ("2", "3", "4", "5"):
                    tr.koy(o, False, "ornek-girdi: " + tr.hazirlik)
                continue
            if tr.t.get("kol") != "deterministik":
                if a.kredi_tavani > 0 and tr.t.get("kol") == "saglayici":
                    sag.append(tr)
                else:
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
        provalar = [tr for tr in det if tr.s["2"][0] and tr.t.get("turetilmis")]
        for tr in provalar:
            prova_kur(tr, bulut)
        sip = [tr for tr in det if tr.s["2"][0]]
        if sip:
            son, _ = kosucu_kos()
            print("KOPRU siparis: %s" % son)
        for tr in det:
            if tr.s["2"][0]:
                olc_4(tr, bulut, gecici)
            else:
                tr.koy("4", False, "onizleme yok -> ORNEK siparis acilmadi")
        kredi = Kredi(bulut, a.kredi_tavani, a.dilim, a.dilim_tavan) if sag else None
        for tr in sag:
            saglayici_2(tr, kredi, devam_is_no=a.devam_is)
            if tr.s["2"][0] and saglayici_4(tr, kredi):
                olc_4(tr, bulut, gecici)
                if a.cikti_dizin and getattr(tr, "dosya_yollari", None):
                    os.makedirs(a.cikti_dizin, exist_ok=True)
                    for ad, y in tr.dosya_yollari.items():
                        if os.path.isfile(y):
                            shutil.copyfile(y, os.path.join(a.cikti_dizin, ad))
                            print("CIKTI %s" % os.path.join(a.cikti_dizin, ad))
            elif tr.s["4"][1] == "OLCULEMEDI":
                tr.koy("4", False, "onizleme yok -> ORNEK uretim acilmadi")
        try:
            tar = tarayici_olc([tr.kod for tr in calisan],
                               {tr.kod: {"is": tr.prova, "tur": tr.kod, "olcu": tr.olcu} for tr in provalar})
            for tr in calisan:
                olc_3_5_6(tr, acik, tar)
        finally:
            for tr in provalar:
                prova_sil(tr, bulut)
        n = 0
        for tr in turler:
            satir = " ".join("%s%s" % (ETIKET[o], "HAZIR" if tr.s[o][0] else "EKSIK") for o in OLCUTLER)
            print("TUR %s %s => %s%s" % (tr.kod, satir, "HAZIR" if tr.hazir() else "EKSIK",
                                         (" is=%s" % tr.is_no) if tr.is_no else ""))
            for o in OLCUTLER:
                print("  %s %s %s" % (ETIKET[o], "HAZIR" if tr.s[o][0] else "EKSIK", tr.s[o][1]))
            n += 1 if tr.hazir() else 0
        rc = 0 if n == len(turler) else 1
        if kredi:
            print("KREDI_HARCANAN=%d/%d taban=%d ayrilan=%d D1_fark=%d" % (
                kredi.harcanan(), kredi.tavan, kredi.taban, kredi.ayrilan, kredi.toplam() - kredi.taban))
            print("DILIM=%s HARCANAN=%d TAVAN=%d" % (kredi.dilim, kredi.dilim_harcanan(), kredi.dilim_tavan))
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
