#!/usr/bin/env python3
"""FOTO URETEC KOSUCUSU (G1, 7 Eki 2026) — Mac'te D/R islerini D1'den ceker, ureteci kosar, R2'ye yazar.

Sozlesme: tools/foto-uretec-sozlesmesi.md (§1 cagri, §2 girdi.json, §3 cikti, §4 akis).
Bagimlilik: stdlib + `npx wrangler` alt sureci (wrangler'in YEREL OAuth'u; yeni secret YOK). Hesap
secimi wrangler'in kendi `CLOUDFLARE_ACCOUNT_ID` ortam degiskeniyle (hesap kimligi repoya YAZILMAZ).

IKI KUYRUK
  siparis  : foto_uretim.asama='uretec-bekliyor' (odeme sonrasi). Girdi: siparisler.urunler kalemi +
             R2 `foto-onizleme/<is_no>.png` (gri harita). Cikti R2 `foto/<siparis>/<kalem>/
             {model.3mf, olcu.json, onizleme.png}` -> asama 'hazir'.
  onizleme : foto_isler.asama='uretec-onizleme' (siparis ONCESI, tarayici onizleyicisi olmayan D/R
             turu). Girdi: R2 `foto-uretec-onizleme/<is_no>/girdi.json` + orada beyan edilen dosyalar.
             Cikti ayni dizine {onizleme.png, olcu.json, model.3mf} -> asama 'onizleme-hazir'
             (model.3mf siparise kadar R2'de bekler). foto_isler'de 'elle' yok: red -> 'basarisiz'.
KOPYA KOLU: siparis kalemi onizleme dizinine bagliysa (R2'de girdi.json VAR) girdi oradan kurulur
  (renk/malzeme/olcu siparisten); olcu.json `girdi_sha256` (koşucunun kanonik girdi parmak izi,
  siparis_no/kalem HARIC) siparis girdisiyle AYNIYSA uretec KOSMAZ, uc dosya kopyalanir (§3 yine
  koşar); farkliysa yeniden uretilir.

KARAR (her is): rc 0 + §3 dogrulamasi gecer -> R2'ye yaz -> CAS ile ilerlet · rc 2 ya da §3 dusmesi
(sizdirmaz:false dahil) -> 'elle' + sebep · diger rc -> deneme+1, DENEME_TAVANI'nda 'elle'.
CAS: is once KIRALANIR (siparis: `guncel`, onizleme: `son_kontrol` jetonu); jeton tutmazsa baska
kosucu ilerletmistir -> o is icin HICBIR yazim yapilmaz. Son yazim da ayni jetona baglidir.

CIKTI (son satir, tek): `HAL=BOS rc=1` · `HAL=PLAN is=<n> rc=0` (KURU, is var) ·
`HAL=ISLEDI uretildi=<n> red=<n> ariza=<n> rc=0` · `HAL=KILITLI rc=3` ·
`HAL=OLCULEMEDI sebep=<kod> rc=4` (D1/R2/wrangler erisilemedi — is KUYRUKTA kalir).
Varsayilan KURU: plan basar, yazmaz. `--uygula` yazar (launchd kurulumu: tools/foto-kosucu-kur.py).
`--hedef onizleme` (8 Eki 2026): D1 + kova shop/wrangler.onizleme.toml'dan (ayri kilit); varsayilan canli.
ORNEK KOLU (8 Eki 2026): siparis_no `ORNEK-<is ilk 12>` + `foto_isler.ziyaretci='ornek'` satiri siparissiz
uretilir; girdi ornek isinin uretec onizlemesinden (yoksa gri haritadan) — ornek_girdisi.

Test kancalari (yalniz hermetik test): FOTO_KOSUCU_WRANGLER (wrangler yerine komut),
FOTO_KOSUCU_URETEC_TABLO (CLI tablosu ek/degisiklik JSON dosyasi), FOTO_KOSUCU_KILIT (kilit yolu),
FOTO_KOSUCU_JENERATOR (uretec deposu), FOTO_KOSUCU_PYTHON (uretec python'u).

TEKIN-ORTAK KOPRUSU (G2, 7 Eki 2026; sozlesme v1 DEGISMEZ): `bicim:"tekin-ortak"` ureteclerinin
(G1-SEMA/G2-SEMA, `<ad>_uret.py --girdi <json> --cikti <dizin>`) kendi girdi JSON'u §2 zarfindan
kurulur — kategori basina TEK esleme fonksiyonu (ESLEMELER, URETEC_CLI'da `esle` adiyla):
  kod      uretec                  olcu_mm ->        form -> uretec alani                renk bolgesi -> alan
  isimlik  isimlik_uret            genislik_mm       satirlar ("\n" ile) · kisa_kenar_mm->     plaka->renk_plaka
                                                     yukseklik_mm · yazi_tipi · plaka_sekli ·  yazi->renk_yazi
                                                     montaj_delikleri
  qr       qr_plaket_uret          plaket_mm         metin · alt_yazi · cerceve               plaka->renk_plaka · kod->renk_qr
  logo     svg_ekstruzyon_uret     uzun_kenar_mm     taban (+ dosyalar.svg -> svg metni)      taban->renk_taban · logo->renk_logo
  muhur    muhur_uret              yuz_mm            sap (sap_renk=ayri sabit)                govde->renk_govde · sap->renk_sap
  sablon   siluet_sablon_uret      uzun_kenar_mm     mod                                      sablon->renk
  yapboz   yapboz_uret             uzun_kenar_mm     parca -> satir x sutun                   yapboz->renkler[0]
Renk ADI -> hex manifestteki TEK tablo `RENK_HEX`ten; tabloda olmayan ad, eslenemeyen secim, sema disi
parametre -> rc 2 (uretec KOSMAZ). Cikti: `uretec.3mf`->`model.3mf`, `ozet.json`->`olcu.json` (§3;
renk_sayisi 3MF'teki extruder sayisi OLCULUR), onizleme >= 1024 px tam sayi kat buyutulur. Uretec
rc 2 -> RET cumlesi RET_KALIPLARI ile koda cevrilir -> `uretec-red:<kod>` (musteri metni manifestte
`URETEC_RED_METIN`; bilinmeyen -> genel metin).
"""
import argparse
import fcntl
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
D1_AD = "pruvo-katalog"
R2_KOVA = "pruvo-ozel"
# HEDEF (8 Eki 2026, `ORNEK-` uctan uca kabulu): varsayilan CANLI (launchd; davranis AYNEN). `--hedef
# onizleme` D1 + kovayi shop/wrangler.onizleme.toml'dan okur (ikinci kopya YOK); toml'da yoksa DUR.
ONIZLEME_TOML = os.path.join(SHOP, "wrangler.onizleme.toml")
HEDEF = "canli"
# ORNEK URETIM (siparissiz; shop/src/foto.js ORNEK_ZIYARETCI / ORNEK_SIPARIS_ONEK ile AYNI): uretim satiri
# siparis_no = ORNEK-<is ilk 12>, siparisler satiri YOK; girdi ornek isinin onizleme girdisinden kurulur.
ORNEK_ZIYARETCI = "ornek"
ORNEK_SIPARIS_ONEK = "ORNEK-"
DENEME_TAVANI = 3
TOLERANS = {"D": 0.01, "R": 0.03}
ONIZLEME_MIN_PX = 1024
URETEC_SURE_SN = 300
IS_SINIRI = 20
LOG_TAVAN_BAYT = 5 * 1024 * 1024
CIKTI_DOSYALARI = ["model.3mf", "olcu.json", "onizleme.png"]
ONIZLEME_DIZIN = "foto-uretec-onizleme/%s/"  # siparis oncesi uretec onizlemesi (shop/src/foto.js ile ayni)
SIPARIS_KALIBI = re.compile(r"^[A-Za-z0-9-]{6,40}$")  # shop/src/foto.js ile ayni
IS_KALIBI = re.compile(r"^[0-9a-f]{32}$")
# Uretec deposu SALT OKUNUR: alt surec __pycache__ yazmaz.
SALT_OKUMA_ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
DOSYA_ADI_KALIBI = re.compile(r"^[a-z_]{1,24}\.(png|jpg|jpeg|svg|wav)$")

# KOMUT ESLEMESI — TEK YER: manifest `uretec` kimligi -> CLI. bicim "sozlesme" = §1 dogal cagri
# (`<komut> --girdi girdi.json --cikti <dizin>`); "litofan" = litofan_uret.py'nin kendi CLI'i
# (--girdi <gri png> --mm --ayak --cikti) + §3 donusumu (litofan.3mf/ozet.json -> model.3mf/olcu.json).
URETEC_CLI = {
    "litofan_uret": {"bicim": "litofan", "betik": "jeneratorler/foto/litofan_uret.py"},
    "isimlik_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/isimlik_uret.py", "esle": "isimlik"},
    "qr_plaket_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/qr_plaket_uret.py", "esle": "qr"},
    "svg_ekstruzyon_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/svg_ekstruzyon_uret.py",
                            "esle": "logo"},
    "muhur_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/muhur_uret.py", "esle": "muhur"},
    "siluet_sablon_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/siluet_sablon_uret.py",
                           "esle": "sablon"},
    "yapboz_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/yapboz_uret.py", "esle": "yapboz"},
    "ozel_uret:kutu": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "kutu", "bayraklar": ["--tur", "kutu"]},
    "ozel_uret:adaptor": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "adaptor", "bayraklar": ["--tur", "adaptor"]},
    "ozel_uret:disli": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "disli", "bayraklar": ["--tur", "disli"]},
    "ozel_uret:kapak": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "kapak", "bayraklar": ["--tur", "kapak"]},
    "ozel_uret:dugme": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "dugme", "bayraklar": ["--tur", "dugme"]},
    "ozel_uret:klips": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "klips", "bayraklar": ["--tur", "klips"]},
    "ozel_uret:saksi": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "saksi", "bayraklar": ["--tur", "saksi"]},
    "rolyef_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g3/rolyef_uret.py", "esle": "rolyef", "bayraklar": []},
    "ses_dalgasi_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g3/ses_dalgasi_uret.py", "esle": "ses", "bayraklar": []},
    "braille_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g3/braille_uret.py", "esle": "braille", "bayraklar": []},
    "topo_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g5/topo_uret.py", "esle": "topo", "on_adim": {"betik": "jeneratorler/ozel_g5/veri_cek.py", "bayraklar": ["--tur", "topo"], "girdi_bayragi": "--girdi", "cikti_bayragi": "--cikti", "ag": True}, "veri_bayragi": "--veri", "bayraklar": []},
    "sehir_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g5/sehir_uret.py", "esle": "sehir", "on_adim": {"betik": "jeneratorler/ozel_g5/veri_cek.py", "bayraklar": ["--tur", "sehir"], "girdi_bayragi": "--girdi", "cikti_bayragi": "--cikti", "ag": True}, "veri_bayragi": "--veri", "bayraklar": []},
    "yildiz_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g5/yildiz_uret.py", "esle": "yildiz", "bayraklar": []},
    "koordinat_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g5/koordinat_uret.py", "esle": "koordinat", "bayraklar": []},
}

NODE_OKU = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "process.stdout.write(JSON.stringify({turler:k.PRUVO_FOTO.turler,renk_hex:k.PRUVO_FOTO.RENK_HEX,"
    "plaka_mm:k.PRUVO_FOTO.PLAKA_MM}));"
)
_MANIFEST = {}


class Erisilemedi(Exception):
    """D1/R2/wrangler erisilemedi — is kuyrukta kalir, satir degismez."""


def simdi_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (int(time.time() * 1000) % 1000)


def sql_metin(v):
    return "'" + str(v).replace("'", "''") + "'"


def _manifest_ham():
    if not _MANIFEST:
        yol = os.path.join(KOK, "foto-uretim-veri.js")
        p = subprocess.run(["node", "-e", NODE_OKU, yol], capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit("manifest okunamadi: " + p.stderr.strip()[:300])
        _MANIFEST.update(json.loads(p.stdout or "{}"))
    return _MANIFEST


def manifest_oku():
    return {t.get("kod"): t for t in _manifest_ham().get("turler") or [] if isinstance(t, dict)}


def renk_tablosu():
    """Manifest `RENK_HEX` (renk ADI -> filament hex) — tek tablo."""
    r = _manifest_ham().get("renk_hex")
    return r if isinstance(r, dict) else {}


def plaka_mm():
    """Manifest `PLAKA_MM` (sozlesme §3 plaka siniri) — tek kaynak; yoksa/bozuksa DUR (fail-closed)."""
    p = _manifest_ham().get("plaka_mm")
    if isinstance(p, bool) or not isinstance(p, (int, float)) or p <= 0:
        raise SystemExit("manifest PLAKA_MM yok/bozuk: %r" % (p,))
    return p


# ------------------------------------------------------------------ wrangler (D1 + R2)
def hedef_kur(hedef):
    """D1_AD / R2_KOVA'yi hedefe gore kurar. onizleme: toml'dan `database_name` + OZEL_DOSYA kovasi."""
    global D1_AD, R2_KOVA, HEDEF
    if hedef == "canli":
        return
    try:
        with open(ONIZLEME_TOML, encoding="utf-8") as f:
            toml = f.read()
    except OSError:
        raise SystemExit("onizleme toml okunamadi: " + ONIZLEME_TOML)
    db = re.search(r'(?m)^database_name\s*=\s*"([a-z0-9-]+)"', toml)
    kova = re.search(r'binding\s*=\s*"OZEL_DOSYA"\s*\n\s*bucket_name\s*=\s*"([a-z0-9-]+)"', toml)
    if not db or not kova or db.group(1) == D1_AD or kova.group(1) == R2_KOVA:
        raise SystemExit("onizleme toml'da ayri D1/kova yok (canliya dusmez): DUR")
    D1_AD, R2_KOVA, HEDEF = db.group(1), kova.group(1), "onizleme"


def wrangler_komutu():
    k = os.environ.get("FOTO_KOSUCU_WRANGLER", "")
    return shlex.split(k) if k else ["npx", "--prefix", SHOP, "wrangler"]


def wr(argumanlar, zaman=180):
    try:
        return subprocess.run(wrangler_komutu() + argumanlar, cwd=SHOP, capture_output=True, text=True,
                              timeout=zaman)
    except (OSError, subprocess.TimeoutExpired):
        raise Erisilemedi("wrangler")


def d1(sql):
    p = wr(["d1", "execute", D1_AD, "--remote", "--json", "--command", sql])
    if p.returncode != 0:
        raise Erisilemedi("d1")
    try:
        v = json.loads(p.stdout)
        blok = v[0] if isinstance(v, list) else v
    except (ValueError, IndexError):
        raise Erisilemedi("d1-json")
    if not isinstance(blok, dict) or blok.get("success") is False:
        raise Erisilemedi("d1")
    return blok.get("results") or [], int((blok.get("meta") or {}).get("changes") or 0)


def r2_al(anahtar, hedef):
    """True = indirildi, False = anahtar YOK; erisim hatasi Erisilemedi."""
    p = wr(["r2", "object", "get", R2_KOVA + "/" + anahtar, "--remote", "--file", hedef])
    if p.returncode != 0:
        if re.search(r"(?i)not\s*found|does not exist|NoSuchKey|\b404\b", p.stdout + p.stderr):
            return False
        raise Erisilemedi("r2")
    return os.path.isfile(hedef)


def r2_koy(anahtar, kaynak, tur):
    p = wr(["r2", "object", "put", R2_KOVA + "/" + anahtar, "--remote", "--file", kaynak,
            "--content-type", tur])
    if p.returncode != 0:
        raise Erisilemedi("r2")


# ------------------------------------------------------------------ is listesi
def isleri_cek(manifest):
    isler = []
    sat, _ = d1("SELECT u.siparis_no, u.kalem, u.is_no, u.tur, u.olcu_mm, u.deneme, u.guncel, s.urunler,"
                " i.ziyaretci AS is_ziyaretci"
                " FROM foto_uretim u LEFT JOIN siparisler s ON s.siparis_no = u.siparis_no"
                " LEFT JOIN foto_isler i ON i.is_no = u.is_no"
                " WHERE u.asama = 'uretec-bekliyor' ORDER BY u.tarih LIMIT " + str(IS_SINIRI))
    for r in sat:
        isler.append({"kuyruk": "siparis", "siparis_no": r.get("siparis_no"), "kalem": r.get("kalem"),
                      "is_no": r.get("is_no"), "tur": r.get("tur"), "olcu_mm": r.get("olcu_mm"),
                      "deneme": int(r.get("deneme") or 0), "gorulen": r.get("guncel") or "",
                      "urunler": r.get("urunler") or "", "is_ziyaretci": r.get("is_ziyaretci") or ""})
    sat, _ = d1("SELECT is_no, tur, olcu_mm, son_kontrol, hata FROM foto_isler"
                " WHERE asama = 'uretec-onizleme' ORDER BY tarih LIMIT " + str(IS_SINIRI))
    for r in sat:
        m = re.match(r"^uretec-ariza-(\d+)$", r.get("hata") or "")
        isler.append({"kuyruk": "onizleme", "is_no": r.get("is_no"), "tur": r.get("tur"),
                      "olcu_mm": r.get("olcu_mm"), "deneme": int(m.group(1)) if m else 0,
                      "gorulen": int(r.get("son_kontrol") or 0)})
    for i in isler:
        t = manifest.get(i["tur"]) or {}
        i["motor"] = t.get("motor", "")
        i["uretec"] = t.get("uretec", "")
    return isler


def is_adi(i):
    if i["kuyruk"] == "siparis":
        return "siparis %s#%s" % (i["siparis_no"], i["kalem"])
    return "onizleme %s" % i["is_no"]


def cikti_anahtarlari(i):
    if i["kuyruk"] == "siparis":
        d = "foto/%s/%s/" % (i["siparis_no"], i["kalem"])
    else:
        d = "foto-uretec-onizleme/%s/" % i["is_no"]
    return {ad: d + ad for ad in CIKTI_DOSYALARI}


def kimlik_gecerli(i):
    if not IS_KALIBI.match(str(i.get("is_no") or "")):
        return False
    if i["kuyruk"] == "siparis":
        return bool(SIPARIS_KALIBI.match(str(i.get("siparis_no") or ""))) and isinstance(i.get("kalem"), int)
    return True


def nerede(i):
    if i["kuyruk"] == "siparis":
        return ("foto_uretim", "siparis_no = %s AND kalem = %d AND asama = 'uretec-bekliyor'"
                % (sql_metin(i["siparis_no"]), i["kalem"]))
    return ("foto_isler", "is_no = %s AND asama = 'uretec-onizleme'" % sql_metin(i["is_no"]))


def jeton_kosulu(i, jeton):
    if i["kuyruk"] == "siparis":
        return "guncel = %s" % sql_metin(jeton)
    return "son_kontrol = %d" % int(jeton)


def yeni_jeton(i):
    if i["kuyruk"] == "siparis":
        j = simdi_iso()
        return j if j != i["gorulen"] else j + "~"
    return max(int(time.time() * 1000), int(i["gorulen"]) + 1)


def sonuc_sql(i, jeton, karar, sebep=""):
    """karar: hazir | elle | ariza. Son yazim jetona bagli (CAS)."""
    tablo, kosul = nerede(i)
    kosul += " AND " + jeton_kosulu(i, jeton)
    simdi = simdi_iso()
    if i["kuyruk"] == "siparis":
        if karar == "hazir":
            st = "asama = 'hazir', sebep = '', deneme = 0, guncel = %s" % sql_metin(simdi)
        elif karar == "elle":
            st = "asama = 'elle', sebep = %s, deneme = 0, guncel = %s" % (sql_metin(sebep), sql_metin(simdi))
        else:
            st = "deneme = deneme + 1, guncel = %s" % sql_metin(simdi)
    else:
        ms = int(time.time() * 1000)
        if karar == "hazir":
            st = "asama = 'onizleme-hazir', hazir_tarih = %s, hata = '', son_kontrol = %d" % (sql_metin(simdi), ms)
        elif karar == "elle":
            st = "asama = 'basarisiz', hata = %s, son_kontrol = %d" % (sql_metin(sebep), ms)
        else:
            st = "hata = %s, son_kontrol = %d" % (sql_metin("uretec-ariza-%d" % (i["deneme"] + 1)), ms)
    return "UPDATE %s SET %s WHERE %s" % (tablo, st, kosul)


def kirala_sql(i, jeton):
    tablo, kosul = nerede(i)
    alan = "guncel = %s" % sql_metin(jeton) if i["kuyruk"] == "siparis" else "son_kontrol = %d" % int(jeton)
    return "UPDATE %s SET %s WHERE %s AND %s" % (tablo, alan, kosul, jeton_kosulu(i, i["gorulen"]))


def geri_ver_sql(i, jeton):
    tablo, kosul = nerede(i)
    alan = ("guncel = %s" % sql_metin(i["gorulen"]) if i["kuyruk"] == "siparis"
            else "son_kontrol = %d" % int(i["gorulen"]))
    return "UPDATE %s SET %s WHERE %s AND %s" % (tablo, alan, kosul, jeton_kosulu(i, jeton))


# ------------------------------------------------------------------ girdi (sozlesme §2)
def siparis_kalemi(urunler, kalem):
    try:
        s = json.loads(urunler or "[]") or []
        k = s[kalem] if isinstance(s, list) and 0 <= kalem < len(s) else None
    except (ValueError, TypeError):
        k = None
    return k if isinstance(k, dict) else None


def siparis_girdisi(i, t):
    """shop/src/foto.js uretecGirdiJson'un AYNASI (kalem seciminden renk/malzeme)."""
    k = siparis_kalemi(i["urunler"], i["kalem"])
    if not k or k.get("foto_is") != i["is_no"]:
        return None
    sc = k.get("foto_secim") if isinstance(k.get("foto_secim"), dict) else {}
    renkler, malzemeler = {}, {}
    for b in t.get("renk_bolgeleri") or []:
        if sc.get(b.get("kod", "") + "_renk"):
            renkler[b["kod"]] = sc[b["kod"] + "_renk"]
    for b in (t.get("malzemeler") or {}):
        if sc.get(b + "_malzeme"):
            malzemeler[b] = sc[b + "_malzeme"]
    return {"sozlesme": 1, "kategori": i["tur"], "siparis_no": i["siparis_no"], "kalem": i["kalem"],
            "olcu_mm": i["olcu_mm"], "renkler": renkler, "malzemeler": malzemeler,
            "parametreler": k.get("parametreler") if isinstance(k.get("parametreler"), dict) else {},
            "dosyalar": {"gri_harita": "gri_harita.png"}}


def ornek_girdisi(i, dizin):
    """ORNEK kolu (siparissiz): satir YALNIZ ornek isine baglanir (`foto_isler.ziyaretci = 'ornek'` ve
    siparis_no = ORNEK-<is ilk 12>; musteri isi bu yoldan URETILEMEZ). Girdi: uretec onizlemesi varsa
    onun girdi.json'u (renk/malzeme/parametre/dosya AYNEN -> kopya kolu calisir), yoksa (tarayici
    onizleyicili tur) R2 `foto-onizleme/<is>.png` gri harita. Donus "" = hazir, aksi red sebebi."""
    if i.get("is_ziyaretci") != ORNEK_ZIYARETCI or i["siparis_no"] != ORNEK_SIPARIS_ONEK + str(i["is_no"])[:12]:
        return "ornek-gecersiz"
    oy = os.path.join(dizin, "girdi.json")
    if r2_al(ONIZLEME_DIZIN % i["is_no"] + "girdi.json", oy):
        try:
            with open(oy, encoding="utf-8") as f:
                g = json.load(f)
        except (OSError, ValueError):
            return "girdi-bozuk"
        if (not isinstance(g, dict) or g.get("kategori") != i["tur"] or g.get("olcu_mm") != i["olcu_mm"] or
                not isinstance(g.get("dosyalar"), dict)):
            return "girdi-bozuk"
        for ad in sorted(set(g["dosyalar"].values())):
            if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad):
                return "girdi-bozuk"
            if not r2_al(ONIZLEME_DIZIN % i["is_no"] + ad, os.path.join(dizin, ad)):
                return "girdi-yok"
        i["onizleme_kaynakli"] = True
    else:
        if not r2_al("foto-onizleme/%s.png" % i["is_no"], os.path.join(dizin, "gri_harita.png")):
            return "girdi-yok"
        g = {"sozlesme": 1, "kategori": i["tur"], "olcu_mm": i["olcu_mm"], "renkler": {}, "malzemeler": {},
             "parametreler": {}, "dosyalar": {"gri_harita": "gri_harita.png"}}
    g["siparis_no"], g["kalem"] = i["siparis_no"], i["kalem"]
    with open(oy, "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, sort_keys=True)
    return ""


def girdi_hazirla(i, t, dizin):
    """Girdi dizinini kurar. Donus "" = hazir, aksi red sebebi. Erisim hatasi Erisilemedi."""
    if i["kuyruk"] == "siparis" and str(i.get("siparis_no") or "").startswith(ORNEK_SIPARIS_ONEK):
        return ornek_girdisi(i, dizin)
    if i["kuyruk"] == "siparis":
        g = siparis_girdisi(i, t)
        if g is None:
            return "kalem-yok"
        oy = os.path.join(dizin, "girdi.json")
        if r2_al(ONIZLEME_DIZIN % i["is_no"] + "girdi.json", oy):
            # Kalem siparis oncesi uretec onizlemesine bagli: parametreler + dosyalar onizleme
            # girdisinden, renk/malzeme/olcu SIPARISTEN (farkliysa sha da farkli -> yeniden uretilir).
            try:
                with open(oy, encoding="utf-8") as f:
                    o = json.load(f)
            except (OSError, ValueError):
                return "girdi-bozuk"
            if not isinstance(o, dict) or o.get("kategori") != i["tur"] or not isinstance(o.get("dosyalar"), dict):
                return "girdi-bozuk"
            g["parametreler"] = o.get("parametreler") if isinstance(o.get("parametreler"), dict) else {}
            g["dosyalar"] = o["dosyalar"]
            for ad in sorted(set(g["dosyalar"].values())):
                if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad):
                    return "girdi-bozuk"
                if not r2_al(ONIZLEME_DIZIN % i["is_no"] + ad, os.path.join(dizin, ad)):
                    return "girdi-yok"
            i["onizleme_kaynakli"] = True
        elif not r2_al("foto-onizleme/%s.png" % i["is_no"], os.path.join(dizin, "gri_harita.png")):
            return "girdi-yok"
    else:
        yol = os.path.join(dizin, "girdi.json")
        if not r2_al("foto-uretec-onizleme/%s/girdi.json" % i["is_no"], yol):
            return "girdi-yok"
        try:
            with open(yol, encoding="utf-8") as f:
                g = json.load(f)
        except (OSError, ValueError):
            return "girdi-bozuk"
        if not isinstance(g, dict) or g.get("kategori") != i["tur"] or g.get("olcu_mm") != i["olcu_mm"]:
            return "girdi-bozuk"
        for ad in sorted(set((g.get("dosyalar") or {}).values())):
            if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad):
                return "girdi-bozuk"
            if not r2_al("foto-uretec-onizleme/%s/%s" % (i["is_no"], ad), os.path.join(dizin, ad)):
                return "girdi-yok"
    with open(os.path.join(dizin, "girdi.json"), "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, sort_keys=True)
    return ""


def girdi_sha(dizin):
    h = hashlib.sha256()
    for ad in sorted(os.listdir(dizin)):
        h.update(ad.encode() + b"\0")
        with open(os.path.join(dizin, ad), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def kanonik_girdi_sha(dizin):
    """Uretimi belirleyen girdinin parmak izi: girdi.json (siparis_no/kalem HARIC) + beyan edilen
    dosyalarin sha256'si. Onizleme ve siparis girdisi AYNI uretimi istiyorsa esittir."""
    with open(os.path.join(dizin, "girdi.json"), encoding="utf-8") as f:
        g = json.load(f)
    oz = {k: g.get(k) for k in ("sozlesme", "kategori", "olcu_mm", "renkler", "malzemeler", "parametreler")}
    oz["dosyalar"] = {}
    for k, ad in sorted((g.get("dosyalar") or {}).items()):
        with open(os.path.join(dizin, ad), "rb") as f:
            oz["dosyalar"][k] = hashlib.sha256(f.read()).hexdigest()
    ham = json.dumps(oz, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()


def girdi_sha_damgala(cikti, sha):
    """olcu.json `girdi_sha256` = koşucunun kanonik girdi parmak izi (kopya kolu bunu karsilastirir)."""
    yol = os.path.join(cikti, "olcu.json")
    try:
        with open(yol, encoding="utf-8") as f:
            o = json.load(f)
    except (OSError, ValueError):
        return  # dogrulama 'olcu-bozuk' der
    if isinstance(o, dict):
        o["girdi_sha256"] = sha
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(o, f, ensure_ascii=False, sort_keys=True)


def onizleme_kopyala(i, sha, cikti):
    """KOPYA KOLU: siparis kalemi siparis oncesi uretec onizlemesine bagliysa VE onizlemenin
    olcu.json `girdi_sha256`'si siparis girdisiyle AYNIYSA uretec KOSMAZ; uc dosya onizleme
    dizininden alinir (§3 dogrulamasi yine koşar). Aksi None -> uretilir."""
    if i["kuyruk"] != "siparis" or not i.get("onizleme_kaynakli"):
        return None
    os.makedirs(cikti)
    for ad in CIKTI_DOSYALARI:
        if not r2_al(ONIZLEME_DIZIN % i["is_no"] + ad, os.path.join(cikti, ad)):
            shutil.rmtree(cikti)
            return None
    try:
        with open(os.path.join(cikti, "olcu.json"), encoding="utf-8") as f:
            onceki = json.load(f).get("girdi_sha256")
    except (OSError, ValueError, AttributeError):
        onceki = None
    if onceki != sha:
        shutil.rmtree(cikti)
        return None
    return 0, "kopya"


# ------------------------------------------------------------------ uretec cagrisi (sozlesme §1)
def cli_tablosu():
    tablo = {k: dict(v) for k, v in URETEC_CLI.items()}
    ek = os.environ.get("FOTO_KOSUCU_URETEC_TABLO", "")
    if ek:
        with open(ek, encoding="utf-8") as f:
            tablo.update(json.load(f))
    return tablo


def uretec_kos(i, girdi_dizin, cikti, t=None):
    """Donus (rc, stderr ozeti). rc 0 ise cikti dizininde §3 dosyalari olmalidir."""
    g = cli_tablosu().get(i["uretec"])
    if not g:
        return 2, "RED uretec-tanimsiz"
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    ham = None
    if g.get("bicim") == "tekin-ortak":
        return tekin_kos(g, t or {}, girdi_dizin, cikti, py, jen)
    if g.get("bicim") == "sozlesme":
        komut = list(g["komut"]) + ["--girdi", os.path.join(girdi_dizin, "girdi.json"), "--cikti", cikti]
    elif g.get("bicim") == "litofan":
        ham = cikti + ".ham"
        komut = [py, os.path.join(jen, g["betik"]), "--girdi", os.path.join(girdi_dizin, "gri_harita.png"),
                 "--mm", str(i["olcu_mm"]), "--ayak", "1", "--cikti", ham]
    else:
        return 2, "RED uretec-bicimi"
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=URETEC_SURE_SN, env=SALT_OKUMA_ENV,
                           cwd=jen if os.path.isdir(jen) else None)
    except subprocess.TimeoutExpired:
        return 1, "sure-asimi"
    except OSError as e:
        return 1, "baslatilamadi: %s" % e
    ozet = (p.stderr.strip().splitlines() or [""])[-1][:200]
    if p.returncode != 0 or ham is None:
        return p.returncode, ozet
    d = subprocess.run([py, os.path.abspath(__file__), "--donustur-litofan", ham, cikti,
                        os.path.join(girdi_dizin, "girdi.json")], capture_output=True, text=True, timeout=120,
                       env=SALT_OKUMA_ENV)
    return (0 if d.returncode == 0 else 1), (d.stderr.strip().splitlines() or [""])[-1][:200]


def donustur_litofan(ham, cikti, girdi_yolu):
    """litofan_uret ciktisi -> sozlesme §3 (uretec python'unda kosar: Pillow orada)."""
    from PIL import Image  # noqa: yalniz donusum kolunda
    with open(girdi_yolu, encoding="utf-8") as f:
        girdi = json.load(f)
    with open(os.path.join(ham, "ozet.json"), encoding="utf-8") as f:
        oz = json.load(f)
    ek = oz.get("ek") if isinstance(oz.get("ek"), dict) else oz
    os.makedirs(cikti)
    shutil.copyfile(os.path.join(ham, "litofan.3mf"), os.path.join(cikti, "model.3mf"))
    im = Image.open(os.path.join(ham, "onizleme.png")).convert("RGB")
    if max(im.size) < ONIZLEME_MIN_PX:
        k = -(-ONIZLEME_MIN_PX // max(im.size))
        im = im.resize((im.size[0] * k, im.size[1] * k), Image.LANCZOS)
    im.save(os.path.join(cikti, "onizleme.png"), format="PNG", optimize=False)
    panel = ek.get("panel_olcu_mm") or [0, 0, 0]
    kutu = oz.get("olcu_mm") or [0, 0, 0]
    hac = oz.get("hacim_mm3")
    hac = sum(hac.values()) if isinstance(hac, dict) else (hac or 0)
    renk = girdi.get("renkler") or {}
    parcalar = [{"ad": "panel", "renk": renk.get("panel", "Beyaz")}]
    if ek.get("ayak_var"):
        parcalar.append({"ad": "ayak", "renk": renk.get("ayak", "Beyaz")})
    with open(os.path.join(cikti, "model.3mf"), "rb") as f:
        msha = hashlib.sha256(f.read()).hexdigest()
    olcu = {"sozlesme": 1, "kategori": girdi.get("kategori"), "uzun_kenar_mm": round(max(panel[0], panel[1]), 3),
            "kutu_mm": {"x": kutu[0], "y": kutu[1], "z": kutu[2]}, "renk_sayisi": len(parcalar),
            "sizdirmaz": oz.get("sizdirmaz") is True, "ucgen": oz.get("ucgen_sayisi"),
            "hacim_cm3": round(hac / 1000.0, 3), "alt_kenar_mm": panel[2], "parcalar": parcalar,
            "girdi_sha256": ek.get("girdi_sha256", ""), "model_sha256": msha}
    with open(os.path.join(cikti, "olcu.json"), "w", encoding="utf-8") as f:
        json.dump(olcu, f, ensure_ascii=False, sort_keys=True)
    return 0


# ------------------------------------------------------------------ tekin-ortak koprusu (G2)
class KopruRed(Exception):
    """Girdi uretece eslenemedi -> rc 2 (uretec KOSMAZ). `kod` URETEC_RED_METIN anahtari."""

    def __init__(self, kod):
        Exception.__init__(self, kod)
        self.kod = kod


def _renk(g, bolge, renk_hex):
    """Bolgenin renk ADI -> hex (RENK_HEX). Bolge secilmemisse None (uretec varsayilani)."""
    ad = (g.get("renkler") or {}).get(bolge)
    if ad is None:
        return None
    if not isinstance(ad, str) or ad not in renk_hex:
        raise KopruRed("renk")
    return renk_hex[ad]


def _secim(p, alan, tablo):
    """Musteri secimi (manifest `secenekler`) -> uretec degeri; secilmemis None, tanimsiz rc 2."""
    if alan not in p:
        return None
    if not isinstance(p[alan], str) or p[alan] not in tablo:
        raise KopruRed("parametre")
    return tablo[p[alan]]


def _koy(d, **alanlar):
    for k, v in alanlar.items():
        if v is not None:
            d[k] = v
    return d


def _gorsel(g, dizin):
    ad = (g.get("dosyalar") or {}).get("foto")
    if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad) or not os.path.isfile(os.path.join(dizin, ad)):
        raise KopruRed("gorsel")
    return os.path.join(os.path.abspath(dizin), ad)


def esle_kutu(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "en_mm": p.get("en_mm") if p.get("en_mm") is not None else 100,
        "boy_mm": p.get("boy_mm") if p.get("boy_mm") is not None else 60,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 40,
        "bolme_x": p.get("bolme_x") if p.get("bolme_x") is not None else 2,
        "bolme_y": p.get("bolme_y") if p.get("bolme_y") is not None else 2,
        "duvar_mm": p.get("duvar_mm") if p.get("duvar_mm") is not None else 1.6,
        "taban_mm": p.get("taban_mm") if p.get("taban_mm") is not None else 1.6,
        "kose_yaricap_mm": p.get("kose_yaricap_mm") if p.get("kose_yaricap_mm") is not None else 3,
        "kapak": bool(p.get("kapak", False))
    }
    return u, []

def esle_adaptor(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "mod": p.get("mod", "burc"),
        "ic_cap_mm": p.get("ic_cap_mm") if p.get("ic_cap_mm") is not None else 10,
        "dis_cap_mm": p.get("dis_cap_mm") if p.get("dis_cap_mm") is not None else 20,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 15,
        "kademe_cap_mm": p.get("kademe_cap_mm") if p.get("kademe_cap_mm") is not None else 14,
        "kademe_yukseklik_mm": p.get("kademe_yukseklik_mm") if p.get("kademe_yukseklik_mm") is not None else 8,
        "ic_cap2_mm": p.get("ic_cap2_mm") if p.get("ic_cap2_mm") is not None else 0,
        "flans": bool(p.get("flans", False)),
        "flans_cap_mm": p.get("flans_cap_mm") if p.get("flans_cap_mm") is not None else 30,
        "flans_kalinlik_mm": p.get("flans_kalinlik_mm") if p.get("flans_kalinlik_mm") is not None else 2
    }
    return u, []

def esle_disli(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "tip": p.get("tip", "duz_disli"),
        "mil_capi_mm": p.get("mil_capi_mm") if p.get("mil_capi_mm") is not None else 5,
        "mil_tipi": p.get("mil_tipi", "yuvarlak"),
        "duz_kesim_mm": p.get("duz_kesim_mm") if p.get("duz_kesim_mm") is not None else 0.5,
        "modul_mm": p.get("modul_mm") if p.get("modul_mm") is not None else 1.5,
        "dis_sayisi": p.get("dis_sayisi") if p.get("dis_sayisi") is not None else 20,
        "kalinlik_mm": p.get("kalinlik_mm") if p.get("kalinlik_mm") is not None else 8,
        "dis_boslugu_mm": p.get("dis_boslugu_mm") if p.get("dis_boslugu_mm") is not None else 0.2,
        "es_dis_sayisi": p.get("es_dis_sayisi") if p.get("es_dis_sayisi") is not None else 0,
        "es_mil_capi_mm": p.get("es_mil_capi_mm") if p.get("es_mil_capi_mm") is not None else 0,
        "kemer_genislik_mm": p.get("kemer_genislik_mm", 6),
        "dis_cap_mm": p.get("dis_cap_mm") if p.get("dis_cap_mm") is not None else 40,
        "v_kanal_genislik_mm": p.get("v_kanal_genislik_mm") if p.get("v_kanal_genislik_mm") is not None else 10,
        "v_kalinlik_mm": p.get("v_kalinlik_mm") if p.get("v_kalinlik_mm") is not None else 16
    }
    return u, []

def esle_kapak(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "mod": p.get("mod", "kapak"),
        "ic_cap_mm": p.get("ic_cap_mm") if p.get("ic_cap_mm") is not None else 20,
        "dis_cap_mm": p.get("dis_cap_mm") if p.get("dis_cap_mm") is not None else 26,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 15,
        "tipa_boyu_mm": p.get("tipa_boyu_mm") if p.get("tipa_boyu_mm") is not None else 12,
        "ust_kalinlik_mm": p.get("ust_kalinlik_mm") if p.get("ust_kalinlik_mm") is not None else 2,
        "gecme_bosluk_mm": p.get("gecme_bosluk_mm") if p.get("gecme_bosluk_mm") is not None else 0.3,
        "cekme_acisi_derece": p.get("cekme_acisi_derece") if p.get("cekme_acisi_derece") is not None else 0,
        "topuz": bool(p.get("topuz", False)),
        "topuz_cap_mm": p.get("topuz_cap_mm") if p.get("topuz_cap_mm") is not None else 12,
        "topuz_yukseklik_mm": p.get("topuz_yukseklik_mm") if p.get("topuz_yukseklik_mm") is not None else 8
    }
    return u, []

def esle_dugme(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "cap_mm": p.get("cap_mm") if p.get("cap_mm") is not None else 30,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 18,
        "tirtil_sayisi": p.get("tirtil_sayisi") if p.get("tirtil_sayisi") is not None else 0,
        "tirtil_derinlik_mm": p.get("tirtil_derinlik_mm") if p.get("tirtil_derinlik_mm") is not None else 1,
        "isaret_cizgisi": bool(p.get("isaret_cizgisi", False)),
        "mil_tipi": p.get("mil_tipi", "d_mil"),
        "mil_capi_mm": p.get("mil_capi_mm") if p.get("mil_capi_mm") is not None else 6,
        "duz_kesim_mm": p.get("duz_kesim_mm") if p.get("duz_kesim_mm") is not None else 0.5,
        "yiv_sayisi": p.get("yiv_sayisi") if p.get("yiv_sayisi") is not None else 18,
        "set_vida": bool(p.get("set_vida", False))
    }
    return u, []

def esle_klips(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "alt_tur": p.get("alt_tur", "boru_kelepcesi"),
        "boru_cap_mm": p.get("boru_cap_mm") if p.get("boru_cap_mm") is not None else 25,
        "agiz_payi_mm": p.get("agiz_payi_mm") if p.get("agiz_payi_mm") is not None else 3,
        "vida": p.get("vida", "M4"),
        "u_aralik_mm": p.get("u_aralik_mm") if p.get("u_aralik_mm") is not None else 4,
        "kol_boyu_mm": p.get("kol_boyu_mm") if p.get("kol_boyu_mm") is not None else 20,
        "kanca_mm": p.get("kanca_mm") if p.get("kanca_mm") is not None else 0.8,
        "genislik_mm": p.get("genislik_mm") if p.get("genislik_mm") is not None else 12,
        "kalinlik_mm": p.get("kalinlik_mm") if p.get("kalinlik_mm") is not None else 3,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 40,
        "kanat_genislik_mm": p.get("kanat_genislik_mm") if p.get("kanat_genislik_mm") is not None else 30,
        "kanat_kalinlik_mm": p.get("kanat_kalinlik_mm") if p.get("kanat_kalinlik_mm") is not None else 3,
        "pim_cap_mm": p.get("pim_cap_mm") if p.get("pim_cap_mm") is not None else 4,
        "eklem_sayisi": p.get("eklem_sayisi", 3),
        "bosluk_mm": p.get("bosluk_mm") if p.get("bosluk_mm") is not None else 0.3,
        "vida_deligi": bool(p.get("vida_deligi", False))
    }
    return u, []

def esle_saksi(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {
        "tur": p.get("tur", "saksi"),
        "cap_mm": p.get("cap_mm") if p.get("cap_mm") is not None else 100,
        "yukseklik_mm": p.get("yukseklik_mm") if p.get("yukseklik_mm") is not None else 100,
        "duvar_mm": p.get("duvar_mm") if p.get("duvar_mm") is not None else 2,
        "taban_mm": p.get("taban_mm") if p.get("taban_mm") is not None else 3,
        "profil": p.get("profil", "silindir"),
        "alt_cap_mm": p.get("alt_cap_mm") if p.get("alt_cap_mm") is not None else 70,
        "oval_orani": p.get("oval_orani") if p.get("oval_orani") is not None else 0.7,
        "bombe_mm": p.get("bombe_mm") if p.get("bombe_mm") is not None else 8,
        "kanal_sayisi": p.get("kanal_sayisi") if p.get("kanal_sayisi") is not None else 0,
        "kanal_derinlik_mm": p.get("kanal_derinlik_mm") if p.get("kanal_derinlik_mm") is not None else 1.5,
        "bukum_derece": p.get("bukum_derece") if p.get("bukum_derece") is not None else 0,
        "drenaj_cap_mm": p.get("drenaj_cap_mm") if p.get("drenaj_cap_mm") is not None else 10,
        "tabak": bool(p.get("tabak", False))
    }
    return u, []

def esle_rolyef(g, dizin, rh):
    p = g.get("parametreler") or {}
    ad = (g.get("dosyalar") or {}).get("foto")
    if not isinstance(ad, str) or not os.path.isfile(os.path.join(dizin, ad)):
        raise KopruRed("gorsel")
    u = {"gorsel": os.path.join(os.path.abspath(dizin), ad),
         "uzun_kenar_mm": float(g["olcu_mm"]),
         "rolyef_yuksekligi_mm": float(p.get("rolyef_yuksekligi_mm", 4.0)),
         "gamma": float(p.get("gamma", 1.0)),
         "otomatik_seviye": bool(p.get("otomatik_seviye", True)),
         "ters": bool(p.get("ters", False)),
         "iki_renk": bool(p.get("iki_renk", False)),
         "esik": float(p.get("esik", 0.5)),
         "renk_taban": _renk(g, "taban", rh) or "#D8D2C4",
         "renk_rolyef": _renk(g, "rolyef", rh) or "#8A5A3C"}
    return u, ["taban", "rolyef"] if u["iki_renk"] else ["taban"]

def esle_ses(g, dizin, rh):
    p = g.get("parametreler") or {}
    ad = (g.get("dosyalar") or {}).get("ses")
    if not isinstance(ad, str) or not os.path.isfile(os.path.join(dizin, ad)):
        raise KopruRed("girdi-yok")
    u = {"wav": os.path.join(os.path.abspath(dizin), ad),
         "uzun_kenar_mm": float(g["olcu_mm"]),
         "cubuk_sayisi": int(p.get("cubuk_sayisi", 100)),
         "dalga_yuksekligi_mm": float(p.get("dalga_yuksekligi_mm", 40.0)),
         "cubuk_yuksekligi_mm": float(p.get("cubuk_yuksekligi_mm", 2.0)),
         "cubuk_genislik_mm": float(p.get("cubuk_genislik_mm", 0.0)),
         "mod": p.get("mod", "simetrik"),
         "normalizasyon": p.get("normalizasyon", "tepe"),
         "kenar_mm": float(p.get("kenar_mm", 6.0)),
         "baslik": p.get("baslik", ""),
         "yazi_tipi": p.get("yazi_tipi", "sans-kalin"),
         "yazi_yuksekligi_mm": float(p.get("yazi_yuksekligi_mm", 8.0)),
         "renk_plaka": _renk(g, "plaka", rh) or "#1F2A44",
         "renk_cubuk": _renk(g, "cubuk", rh) or "#E8E4D8",
         "renk_yazi": _renk(g, "yazi", rh) or ""}
    return u, ["plaka", "cubuk"]

def esle_braille(g, dizin, rh):
    p = g.get("parametreler") or {}
    m = p.get("metin", "")
    if not isinstance(m, str) or not m.strip():
        raise KopruRed("parametre")
    u = {"metin": m, "uzun_kenar_mm": float(g["olcu_mm"]),
         "kenar_mm": float(p.get("kenar_mm", 6.0)),
         "buyuk_harf": bool(p.get("buyuk_harf", False)),
         "hizalama": p.get("hizalama", "sol"),
         "yazi_tipi": p.get("yazi_tipi", "sans-kalin"),
         "ust_yazi": p.get("ust_yazi", ""),
         "renk_plaka": _renk(g, "plaka", rh) or "#1A1A1A",
         "renk_nokta": _renk(g, "nokta", rh) or "#E8E4D8",
         "renk_yazi": _renk(g, "yazi", rh) or ""}
    return u, ["plaka", "nokta"]

def esle_topo(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"uzun_kenar_mm": float(g["olcu_mm"]),
          "plaka_sekli": p.get("plaka_sekli", "kare"),
          "cerceve_mm": float(p.get("cerceve_mm", 4.0)),
          "renk_taban": _renk(g, "taban", rh) or "#D8D2C4",
          "renk_yazi": _renk(g, "yazi", rh) or "#8A5A3C"}
    if "enlem" in p and "boylam" in p:
        u["enlem"] = float(p["enlem"]); u["boylam"] = float(p["boylam"])
    if "yaricap_km" in p: u["yaricap_km"] = float(p["yaricap_km"])
    if "tarih" in p: u["tarih"] = p["tarih"]
    if "konum_ad" in p: u["konum_ad"] = p["konum_ad"]
    return u, ["taban", "yazi"]

def esle_sehir(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"uzun_kenar_mm": float(g["olcu_mm"]),
          "plaka_sekli": p.get("plaka_sekli", "kare"),
          "cerceve_mm": float(p.get("cerceve_mm", 4.0)),
          "renk_taban": _renk(g, "taban", rh) or "#D8D2C4",
          "renk_yazi": _renk(g, "yazi", rh) or "#8A5A3C"}
    if "enlem" in p and "boylam" in p:
        u["enlem"] = float(p["enlem"]); u["boylam"] = float(p["boylam"])
    if "yaricap_km" in p: u["yaricap_km"] = float(p["yaricap_km"])
    if "tarih" in p: u["tarih"] = p["tarih"]
    if "konum_ad" in p: u["konum_ad"] = p["konum_ad"]
    return u, ["taban", "yazi"]

def esle_yildiz(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"uzun_kenar_mm": float(g["olcu_mm"]),
          "plaka_sekli": p.get("plaka_sekli", "kare"),
          "cerceve_mm": float(p.get("cerceve_mm", 4.0)),
          "renk_taban": _renk(g, "taban", rh) or "#D8D2C4",
          "renk_yazi": _renk(g, "yazi", rh) or "#8A5A3C"}
    if "enlem" in p and "boylam" in p:
        u["enlem"] = float(p["enlem"]); u["boylam"] = float(p["boylam"])
    if "yaricap_km" in p: u["yaricap_km"] = float(p["yaricap_km"])
    if "tarih" in p: u["tarih"] = p["tarih"]
    if "konum_ad" in p: u["konum_ad"] = p["konum_ad"]
    return u, ["taban", "yazi"]

def esle_koordinat(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"uzun_kenar_mm": float(g["olcu_mm"]),
          "plaka_sekli": p.get("plaka_sekli", "kare"),
          "cerceve_mm": float(p.get("cerceve_mm", 4.0)),
          "renk_taban": _renk(g, "taban", rh) or "#D8D2C4",
          "renk_yazi": _renk(g, "yazi", rh) or "#8A5A3C"}
    if "enlem" in p and "boylam" in p:
        u["enlem"] = float(p["enlem"]); u["boylam"] = float(p["boylam"])
    if "yaricap_km" in p: u["yaricap_km"] = float(p["yaricap_km"])
    if "tarih" in p: u["tarih"] = p["tarih"]
    if "konum_ad" in p: u["konum_ad"] = p["konum_ad"]
    return u, ["taban", "yazi"]



VAR_YOK = {"Var": True, "Yok": False}


def esle_isimlik(g, dizin, rh):
    p = g.get("parametreler") or {}
    s, kisa = p.get("satirlar"), p.get("kisa_kenar_mm")
    if not isinstance(s, str) or not s.strip():
        raise KopruRed("parametre")
    if isinstance(kisa, bool) or not isinstance(kisa, (int, float)):
        raise KopruRed("parametre")
    if kisa > g["olcu_mm"]:
        raise KopruRed("kisa-kenar")
    u = {"satirlar": s.split("\n"), "genislik_mm": float(g["olcu_mm"]), "yukseklik_mm": float(kisa)}
    _koy(u, yazi_tipi=_secim(p, "yazi_tipi", {"Düz": "sans-kalin", "Tırnaklı": "serif-kalin"}),
         plaka_sekli=_secim(p, "plaka_sekli", {"Dikdörtgen": "dikdortgen", "Yuvarlak köşe": "yuvarlak-kose",
                                                "Oval": "oval"}),
         montaj_delikleri=_secim(p, "montaj_delikleri", VAR_YOK),
         renk_plaka=_renk(g, "plaka", rh), renk_yazi=_renk(g, "yazi", rh))
    return u, ["plaka", "yazi"]


def esle_qr(g, dizin, rh):
    p = g.get("parametreler") or {}
    m = p.get("metin")
    if not isinstance(m, str) or not m.strip():
        raise KopruRed("parametre")
    if len(m.encode("utf-8")) > 150:
        raise KopruRed("qr-uzun")
    a = p.get("alt_yazi")
    u = {"metin": m, "plaket_mm": float(g["olcu_mm"])}
    _koy(u, alt_yazi=a if isinstance(a, str) and a else None, cerceve=_secim(p, "cerceve", VAR_YOK),
         renk_plaka=_renk(g, "plaka", rh), renk_qr=_renk(g, "kod", rh))
    return u, ["plaka", "kod"]


def esle_logo(g, dizin, rh):
    p = g.get("parametreler") or {}
    ad = (g.get("dosyalar") or {}).get("svg")
    if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad):
        raise KopruRed("svg")
    try:
        with open(os.path.join(dizin, ad), encoding="utf-8") as f:
            svg = f.read()
    except (OSError, UnicodeDecodeError):
        raise KopruRed("svg")
    taban = _secim(p, "taban", VAR_YOK)
    u = {"svg": svg, "uzun_kenar_mm": float(g["olcu_mm"])}
    _koy(u, taban=taban, renk_taban=_renk(g, "taban", rh) if taban else None, renk_logo=_renk(g, "logo", rh))
    return u, (["taban", "logo"] if taban else ["logo"])


def esle_muhur(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"gorsel": _gorsel(g, dizin), "yuz_mm": float(g["olcu_mm"]), "sap_renk": "ayri"}
    _koy(u, sap=_secim(p, "sap", {"Silindir": "silindir", "Topuz": "topuz"}),
         renk_govde=_renk(g, "govde", rh), renk_sap=_renk(g, "sap", rh))
    return u, ["govde", "sap"]


def esle_sablon(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"gorsel": _gorsel(g, dizin), "uzun_kenar_mm": float(g["olcu_mm"])}
    _koy(u, mod=_secim(p, "mod", {"Delikli": "pozitif", "Dolu silüet": "negatif"}), renk=_renk(g, "sablon", rh))
    return u, ["sablon"]


def esle_yapboz(g, dizin, rh):
    p = g.get("parametreler") or {}
    u = {"gorsel": _gorsel(g, dizin), "uzun_kenar_mm": float(g["olcu_mm"])}
    sc = _secim(p, "parca", {"12": (3, 4), "20": (4, 5), "30": (5, 6)})
    if sc:
        u["satir"], u["sutun"] = sc
    r = _renk(g, "yapboz", rh)
    if r:
        u["renkler"] = [r]
    return u, ["yapboz"]


# KATEGORI BASINA TEK esleme fonksiyonu (URETEC_CLI `esle` buradan secer).
ESLEMELER = {"isimlik": esle_isimlik, "qr": esle_qr, "logo": esle_logo, "muhur": esle_muhur,
             "sablon": esle_sablon, "yapboz": esle_yapboz,
             "kutu": esle_kutu,
             "adaptor": esle_adaptor,
             "disli": esle_disli,
             "kapak": esle_kapak,
             "dugme": esle_dugme,
             "klips": esle_klips,
             "saksi": esle_saksi,
             "rolyef": esle_rolyef,
             "ses": esle_ses,
             "braille": esle_braille,
             "topo": esle_topo,
             "sehir": esle_sehir,
             "yildiz": esle_yildiz,
             "koordinat": esle_koordinat,
             "bust": esle_rolyef}

# Uretec RET cumlesi -> red kodu (ilk eslesen; manifest URETEC_RED_METIN anahtari). Yok -> "genel".
RET_KALIPLARI = [
    (r"kontrast", "kontrast"),
    (r"parca kisa kenari|satir\*sutun|parca tabladan", "parca"),
    (r"metin cok uzun|modul boyutu", "qr-uzun"),
    (r"fontta bulunmayan|denetim/gorunmez|surrogate", "karakter"),
    (r"yazi|satir|harf", "metin-sigmadi"),
    (r"ince cizgi|ink kisa kenari", "ince-cizgi"),
    (r"koprusuz|yuzen ada", "kopru"),
    (r"oran", "oran"),
    (r"svg", "svg"),
    (r"gorsel|ink|siluet|kontur|maske", "gorsel"),
]


def ret_kodu(metin):
    m = re.sub(r"^\s*(?:RET|RED):?\s*", "", metin or "").lower()
    for kalip, kod in RET_KALIPLARI:
        if re.search(kalip, m):
            return kod
    return "genel"


def tekin_kos(g, t, girdi_dizin, cikti, py, jen):
    """§2 zarfi -> uretecin kendi JSON'u -> uretec -> §3 donusumu. Donus (rc, ozet)."""
    with open(os.path.join(girdi_dizin, "girdi.json"), encoding="utf-8") as f:
        girdi = json.load(f)
    fn = ESLEMELER.get(g.get("esle"))
    if not fn:
        return 2, "RED uretec-bicimi"
    try:
        form = t.get("form") if isinstance(t.get("form"), dict) else {}
        if any(k not in form for k in (girdi.get("parametreler") or {})):
            raise KopruRed("parametre")
        u, bolgeler = fn(girdi, girdi_dizin, renk_tablosu())
    except KopruRed as e:
        return 2, "RED %s: kopru" % e.kod
    ham, ugirdi, kopru = cikti + ".ham", cikti + ".uretec-girdi.json", cikti + ".kopru.json"
    with open(ugirdi, "w", encoding="utf-8") as f:
        json.dump(u, f, ensure_ascii=False, sort_keys=True)
    with open(kopru, "w", encoding="utf-8") as f:
        json.dump({"bolgeler": bolgeler}, f)
    komut = [py, os.path.join(jen, g["betik"])] + list(g.get("bayraklar", []))
    # 8 Eki 2026: G5 topo/sehir iki asamali (veri_cek.py --tur ... --girdi ... --cikti <veri.json>; ag:true)
    if g.get("on_adim"):
        oa = g["on_adim"]
        veri_yol = cikti + ".veri.json"
        oa_komut = [py, os.path.join(jen, oa["betik"])] + list(oa.get("bayraklar", []))
        oa_komut += [oa["girdi_bayragi"], os.path.join(girdi_dizin, "girdi.json"),
                     oa["cikti_bayragi"], veri_yol]
        try:
            p_oa = subprocess.run(oa_komut, capture_output=True, text=True, timeout=URETEC_SURE_SN, env=SALT_OKUMA_ENV,
                                  cwd=jen if os.path.isdir(jen) else None)
        except subprocess.TimeoutExpired:
            return 1, "on-adim sure-asimi"
        except OSError as e:
            return 1, "on-adim baslatilamadi: %s" % e
        if p_oa.returncode != 0:
            return 2, "RED on-adim: " + (p_oa.stderr.strip().splitlines() or [""])[-1][:200]
        komut += [g["veri_bayragi"], veri_yol]
    komut += ["--girdi", ugirdi, "--cikti", ham]
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=URETEC_SURE_SN, env=SALT_OKUMA_ENV,
                           cwd=jen if os.path.isdir(jen) else None)
    except subprocess.TimeoutExpired:
        return 1, "sure-asimi"
    except OSError as e:
        return 1, "baslatilamadi: %s" % e
    ozet = (p.stderr.strip().splitlines() or [""])[-1][:200]
    if p.returncode == 2:
        return 2, "RED %s: %s" % (ret_kodu(ozet), ozet)
    if p.returncode != 0:
        return p.returncode, ozet
    d = subprocess.run([py, os.path.abspath(__file__), "--donustur-tekin", ham, cikti,
                        os.path.join(girdi_dizin, "girdi.json"), kopru], capture_output=True, text=True,
                       timeout=120, env=SALT_OKUMA_ENV)
    return (0 if d.returncode == 0 else 1), (d.stderr.strip().splitlines() or [""])[-1][:200]


def uc_mf_extruder_sayisi(yol):
    """3MF'teki FARKLI extruder sayisi (Metadata/model_settings.config) — OLCULUR; yoksa 0."""
    import zipfile
    try:
        with zipfile.ZipFile(yol) as z:
            s = z.read("Metadata/model_settings.config").decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return 0
    return len(set(re.findall(r'key="extruder"\s+value="(\d+)"', s)))


def uc_mf_uzun_kenar(yol, oz):
    """Uzun kenar 3MF GEOMETRISINDEN olculur (ozetteki nominal degil; 7 Eki mimar karari 3): dunya
    koordinatinda (component + build donusumu) x/y kutusunun buyuk kenari. Parcalar tablada raf
    duzenindeyse (yapboz) ozet.parcalar[].tasima_mm cikarilarak BIRLESIK urun olculur. Geometri
    okunamazsa None (dogrulama uzun-kenar-tolerans ile duser)."""
    import zipfile
    try:
        with zipfile.ZipFile(yol) as z:
            ad = [n for n in z.namelist() if n.endswith(".model")]
            xml = z.read(ad[0]).decode("utf-8") if ad else ""
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return None
    nesne = {}
    for m in re.finditer(r'<object\b([^>]*)>(.*?)</object>', xml, re.S):
        oid = re.search(r'\bid="(\d+)"', m.group(1))
        if not oid:
            continue
        isim = re.search(r'\bname="([^"]*)"', m.group(1))
        vs = [tuple(float(c) for c in t) for t in re.findall(
            r'<vertex\s+x="([-0-9.eE+]+)"\s+y="([-0-9.eE+]+)"\s+z="([-0-9.eE+]+)"', m.group(2))]
        komp = re.findall(r'<component\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', m.group(2))
        nesne[oid.group(1)] = (isim.group(1) if isim else oid.group(1), vs, komp)

    def donustur(p, t):
        if not t:
            return p
        a = [float(x) for x in t.split()]
        return (p[0] * a[0] + p[1] * a[3] + p[2] * a[6] + a[9], p[0] * a[1] + p[1] * a[4] + p[2] * a[7] + a[10],
                p[0] * a[2] + p[1] * a[5] + p[2] * a[8] + a[11])

    def noktalar(oid, t, derinlik=0):
        if oid not in nesne or derinlik > 8:
            return []
        _, vs, komp = nesne[oid]
        out = list(vs)
        for cid, ct in komp:
            out += noktalar(cid, ct, derinlik + 1)
        return [donustur(p, t) for p in out]

    tasima = {p.get("ad"): p.get("tasima_mm") for p in (oz.get("parcalar") or []) if isinstance(p, dict)}
    mn, mx = [float("inf")] * 2, [float("-inf")] * 2
    for b in re.finditer(r'<item\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', xml):
        ps = noktalar(b.group(1), b.group(2))
        tas = tasima.get(nesne.get(b.group(1), ("",))[0]) or [0.0, 0.0, 0.0]
        for p in ps:
            for i in (0, 1):
                mn[i] = min(mn[i], p[i] - tas[i])
                mx[i] = max(mx[i], p[i] - tas[i])
    if mn[0] == float("inf"):
        return None
    return max(mx[0] - mn[0], mx[1] - mn[1])


def donustur_tekin(ham, cikti, girdi_yolu, kopru_yolu):
    """tekin-ortak uretec ciktisi -> sozlesme §3 (uretec python'unda kosar; Pillow YALNIZ buyutmede)."""
    with open(girdi_yolu, encoding="utf-8") as f:
        girdi = json.load(f)
    with open(kopru_yolu, encoding="utf-8") as f:
        bolgeler = json.load(f).get("bolgeler") or []
    with open(os.path.join(ham, "ozet.json"), encoding="utf-8") as f:
        oz = json.load(f)
    os.makedirs(cikti)
    shutil.copyfile(os.path.join(ham, "uretec.3mf"), os.path.join(cikti, "model.3mf"))
    b = png_boyut(os.path.join(ham, "onizleme.png"))
    if b and max(b) >= ONIZLEME_MIN_PX:
        shutil.copyfile(os.path.join(ham, "onizleme.png"), os.path.join(cikti, "onizleme.png"))
    else:
        from PIL import Image  # noqa: yalniz buyutme kolunda (uretec onizlemesi <= 800 px)
        im = Image.open(os.path.join(ham, "onizleme.png")).convert("RGB")
        k = -(-ONIZLEME_MIN_PX // max(im.size))
        im = im.resize((im.size[0] * k, im.size[1] * k), Image.LANCZOS)
        im.save(os.path.join(cikti, "onizleme.png"), format="PNG", optimize=False)
    kutu = oz.get("olcu_mm") or [0, 0, 0]
    uk = uc_mf_uzun_kenar(os.path.join(cikti, "model.3mf"), oz)
    hac = oz.get("hacim_mm3")
    if isinstance(hac, dict):
        hac = hac["toplam"] if "toplam" in hac else sum(hac.values())
    renk = girdi.get("renkler") or {}
    with open(os.path.join(cikti, "model.3mf"), "rb") as f:
        msha = hashlib.sha256(f.read()).hexdigest()
    olcu = {"sozlesme": 1, "kategori": girdi.get("kategori"), "uzun_kenar_mm": round(uk, 3) if uk is not None else None,
            "kutu_mm": {"x": kutu[0], "y": kutu[1], "z": kutu[2]},
            "renk_sayisi": uc_mf_extruder_sayisi(os.path.join(cikti, "model.3mf")),
            "sizdirmaz": oz.get("sizdirmaz") is True, "ucgen": oz.get("ucgen_sayisi"),
            "hacim_cm3": round((hac or 0) / 1000.0, 3), "alt_kenar_mm": kutu[2],
            "parcalar": [{"ad": b, "renk": renk.get(b, "")} for b in bolgeler],
            "girdi_sha256": "", "model_sha256": msha}
    with open(os.path.join(cikti, "olcu.json"), "w", encoding="utf-8") as f:
        json.dump(olcu, f, ensure_ascii=False, sort_keys=True)
    return 0


# ------------------------------------------------------------------ dogrulama (sozlesme §3)
def png_boyut(yol):
    with open(yol, "rb") as f:
        b = f.read(24)
    if len(b) < 24 or b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", b[16:24])


def cikti_dogrula(i, t, cikti):
    """Donus "" = gecerli, aksi sebep (shop/src/foto.js uretecOlcuDogrula + dosya sartlari)."""
    if not os.path.isdir(cikti) or sorted(os.listdir(cikti)) != CIKTI_DOSYALARI:
        return "cikti-eksik"
    with open(os.path.join(cikti, "model.3mf"), "rb") as f:
        if f.read(4) != b"PK\x03\x04":
            return "gecersiz-3mf"
    b = png_boyut(os.path.join(cikti, "onizleme.png"))
    if not b or max(b) < ONIZLEME_MIN_PX:
        return "gecersiz-onizleme"
    try:
        with open(os.path.join(cikti, "olcu.json"), encoding="utf-8") as f:
            o = json.load(f)
    except (OSError, ValueError):
        return "olcu-bozuk"
    if not isinstance(o, dict) or o.get("sozlesme") != 1:
        return "olcu-bozuk"
    if o.get("kategori") != i["tur"]:
        return "kategori-uyusmaz"
    if o.get("sizdirmaz") is not True:
        return "sizdirmaz-degil"
    a = t.get("olcu_mm") or {}
    if not (isinstance(i["olcu_mm"], int) and a.get("en_az", 1) <= i["olcu_mm"] <= a.get("en_cok", 0)):
        return "olcu-aralik-disi"
    tol = TOLERANS.get(t.get("motor"))
    uk = o.get("uzun_kenar_mm")
    if not tol or not isinstance(uk, (int, float)) or abs(uk - i["olcu_mm"]) > i["olcu_mm"] * tol + 1e-9:
        return "uzun-kenar-tolerans"
    rs = o.get("renk_sayisi")
    if not isinstance(rs, int) or isinstance(rs, bool) or not 1 <= rs <= 4:
        return "renk-fazla"
    k = o.get("kutu_mm") or {}
    if not all(isinstance(k.get(e), (int, float)) and 0 < k[e] <= plaka_mm() for e in ("x", "y")):
        return "plaka-disi"
    return ""


# ------------------------------------------------------------------ is isleme
def red_sebebi(stderr):
    m = re.match(r"^(?:RED|RET):?\s*([a-z0-9-]{1,40})", stderr or "")
    return "uretec-red:" + m.group(1) if m else "uretec-red"


def plan_bas(i, yaz):
    a = cikti_anahtarlari(i)
    yaz("IS %s tur=%s olcu=%s motor=%s uretec=%s deneme=%d"
        % (is_adi(i), i["tur"], i["olcu_mm"], i["motor"] or "-", i["uretec"] or "-", i["deneme"]))
    for ad in CIKTI_DOSYALARI:
        yaz("  PLAN R2 PUT %s/%s" % (R2_KOVA, a[ad]))
    yaz("  PLAN D1 %s" % sonuc_sql(i, "<jeton>" if i["kuyruk"] == "siparis" else 0, "hazir"))


def is_isle(i, manifest, yaz):
    """Donus: 'uretildi' | 'red' | 'ariza' | 'cas' (baska kosucu ilerletmis, yazim yok)."""
    t = manifest.get(i["tur"]) or {}
    if not kimlik_gecerli(i):
        yaz("ATLA %s kimlik-gecersiz" % is_adi(i))
        return "cas"
    jeton = yeni_jeton(i)
    _, n = d1(kirala_sql(i, jeton))
    if n != 1:
        yaz("CAS %s kiralanamadi (baska kosucu ilerletmis) — yazim yok" % is_adi(i))
        return "cas"
    gecici = tempfile.mkdtemp(prefix="foto-kosucu-")
    try:
        girdi_dizin = os.path.join(gecici, "girdi")
        os.makedirs(girdi_dizin)
        cikti = os.path.join(gecici, "cikti")
        sebep = girdi_hazirla(i, t, girdi_dizin) if t.get("motor") in TOLERANS else "kol-uygun-degil"
        if sebep:
            rc, ozet = 2, "RED " + sebep
        else:
            sha = kanonik_girdi_sha(girdi_dizin)
            rc, ozet = onizleme_kopyala(i, sha, cikti) or uretec_kos(i, girdi_dizin, cikti, t)
            if rc == 0:
                girdi_sha_damgala(cikti, sha)
        if rc == 0:
            sebep = cikti_dogrula(i, t, cikti)
            if not sebep:
                a = cikti_anahtarlari(i)
                tur = {"model.3mf": "model/3mf", "olcu.json": "application/json", "onizleme.png": "image/png"}
                for ad in CIKTI_DOSYALARI:
                    r2_koy(a[ad], os.path.join(cikti, ad), tur[ad])
                karar = "hazir"
            else:
                karar = "elle"
        elif rc == 2:
            sebep = sebep or red_sebebi(ozet)
            karar = "elle"
        else:
            karar = "elle" if i["deneme"] + 1 >= DENEME_TAVANI else "ariza"
            sebep = "uretec-ariza"
        _, n = d1(sonuc_sql(i, jeton, karar, sebep))
        if n != 1:
            yaz("CAS %s son yazim tutmadi (jeton degismis)" % is_adi(i))
            return "cas"
        yaz("%s %s%s%s" % (karar.upper(), is_adi(i), (" sebep=" + sebep) if sebep else "",
                          " KOPYA (uretec kosmadi)" if ozet == "kopya" else "")
            + ("" if karar == "hazir" else " rc=%s %s" % (rc, ozet)))
        return {"hazir": "uretildi", "elle": "red" if rc == 0 or rc == 2 else "ariza", "ariza": "ariza"}[karar]
    except Erisilemedi:
        try:
            d1(geri_ver_sql(i, jeton))
        except Erisilemedi:
            pass
        raise
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# ------------------------------------------------------------------ kilit + log
def kilit_al():
    ad = "pruvo-foto-kosucu.kilit" if HEDEF == "canli" else "pruvo-foto-kosucu-%s.kilit" % HEDEF
    yol = os.environ.get("FOTO_KOSUCU_KILIT") or os.path.join(tempfile.gettempdir(), ad)
    fd = os.open(yol, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    # flock surec olunce cekirdekce birakilir: bayat PID'in kilidi kendiliginden devralinir.
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def log_dondur(yol, tavan=LOG_TAVAN_BAYT):
    """Tek log <= tavan: asilirsa eskisi (.1) SILINIR, mevcut .1 olur (en cok iki dosya)."""
    try:
        if os.path.getsize(yol) >= tavan:
            os.replace(yol, yol + ".1")
    except OSError:
        pass


def calistir(uygula, yaz):
    fd = kilit_al()
    if fd is None:
        return "HAL=KILITLI rc=3", 3
    try:
        manifest = manifest_oku()
        try:
            isler = isleri_cek(manifest)
        except Erisilemedi as e:
            return "HAL=OLCULEMEDI sebep=%s rc=4" % e, 4
        if not isler:
            return "HAL=BOS rc=1", 1
        if not uygula:
            for i in isler:
                plan_bas(i, yaz)
            yaz("KURU: yazim 0 (--uygula yazar)")
            return "HAL=PLAN is=%d rc=0" % len(isler), 0
        say = {"uretildi": 0, "red": 0, "ariza": 0, "cas": 0}
        for i in isler:
            try:
                say[is_isle(i, manifest, yaz)] += 1
            except Erisilemedi as e:
                yaz("DUR %s erisim yok (%s) — is kuyrukta" % (is_adi(i), e))
                return "HAL=OLCULEMEDI sebep=%s rc=4" % e, 4
        return "HAL=ISLEDI uretildi=%d red=%d ariza=%d rc=0" % (say["uretildi"], say["red"], say["ariza"]), 0
    finally:
        os.close(fd)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Foto uretec kosucusu (varsayilan KURU)")
    ap.add_argument("--uygula", action="store_true", help="D1/R2'ye YAZ (yalniz launchd / mimar)")
    ap.add_argument("--log", help="ciktiyi bu dosyaya ekle (5 MB tavan, eskisi silinir)")
    ap.add_argument("--hedef", choices=["canli", "onizleme"], default="canli",
                    help="D1/R2 hedefi (onizleme: shop/wrangler.onizleme.toml; varsayilan canli)")
    ap.add_argument("--donustur-litofan", nargs=3, metavar=("HAM", "CIKTI", "GIRDI"), help=argparse.SUPPRESS)
    ap.add_argument("--donustur-tekin", nargs=4, metavar=("HAM", "CIKTI", "GIRDI", "KOPRU"), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.donustur_litofan:
        return donustur_litofan(*a.donustur_litofan)
    if a.donustur_tekin:
        return donustur_tekin(*a.donustur_tekin)
    hedef_kur(a.hedef)
    tampon = io.StringIO()

    def yaz(s):
        print(s)
        tampon.write(s + "\n")

    satir, rc = calistir(a.uygula, yaz)
    yaz(satir)
    if a.log:
        log_dondur(a.log)
        with open(a.log, "a", encoding="utf-8") as f:
            f.write("# %s\n%s" % (simdi_iso(), tampon.getvalue()))
    return rc


if __name__ == "__main__":
    sys.exit(main())
