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

KARAR (her is): rc 0 + §3 dogrulamasi gecer -> R2'ye yaz -> CAS ile ilerlet · rc 2 ya da §3 dusmesi
(sizdirmaz:false dahil) -> 'elle' + sebep · diger rc -> deneme+1, DENEME_TAVANI'nda 'elle'.
CAS: is once KIRALANIR (siparis: `guncel`, onizleme: `son_kontrol` jetonu); jeton tutmazsa baska
kosucu ilerletmistir -> o is icin HICBIR yazim yapilmaz. Son yazim da ayni jetona baglidir.

CIKTI (son satir, tek): `HAL=BOS rc=1` · `HAL=PLAN is=<n> rc=0` (KURU, is var) ·
`HAL=ISLEDI uretildi=<n> red=<n> ariza=<n> rc=0` · `HAL=KILITLI rc=3` ·
`HAL=OLCULEMEDI sebep=<kod> rc=4` (D1/R2/wrangler erisilemedi — is KUYRUKTA kalir).
Varsayilan KURU: plan basar, yazmaz. `--uygula` yazar (launchd kurulumu: tools/foto-kosucu-kur.py).

Test kancalari (yalniz hermetik test): FOTO_KOSUCU_WRANGLER (wrangler yerine komut),
FOTO_KOSUCU_URETEC_TABLO (CLI tablosu ek/degisiklik JSON dosyasi), FOTO_KOSUCU_KILIT (kilit yolu),
FOTO_KOSUCU_JENERATOR (uretec deposu), FOTO_KOSUCU_PYTHON (uretec python'u).
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
DENEME_TAVANI = 3
TOLERANS = {"D": 0.01, "R": 0.03}
PLAKA_MM = 250
ONIZLEME_MIN_PX = 1024
URETEC_SURE_SN = 300
IS_SINIRI = 20
LOG_TAVAN_BAYT = 5 * 1024 * 1024
CIKTI_DOSYALARI = ["model.3mf", "olcu.json", "onizleme.png"]
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
}

NODE_OKU = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "process.stdout.write(JSON.stringify(k.PRUVO_FOTO.turler));"
)


class Erisilemedi(Exception):
    """D1/R2/wrangler erisilemedi — is kuyrukta kalir, satir degismez."""


def simdi_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (int(time.time() * 1000) % 1000)


def sql_metin(v):
    return "'" + str(v).replace("'", "''") + "'"


def manifest_oku():
    yol = os.path.join(KOK, "foto-uretim-veri.js")
    p = subprocess.run(["node", "-e", NODE_OKU, yol], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("manifest okunamadi: " + p.stderr.strip()[:300])
    return {t.get("kod"): t for t in json.loads(p.stdout or "[]") if isinstance(t, dict)}


# ------------------------------------------------------------------ wrangler (D1 + R2)
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
    sat, _ = d1("SELECT u.siparis_no, u.kalem, u.is_no, u.tur, u.olcu_mm, u.deneme, u.guncel, s.urunler"
                " FROM foto_uretim u LEFT JOIN siparisler s ON s.siparis_no = u.siparis_no"
                " WHERE u.asama = 'uretec-bekliyor' ORDER BY u.tarih LIMIT " + str(IS_SINIRI))
    for r in sat:
        isler.append({"kuyruk": "siparis", "siparis_no": r.get("siparis_no"), "kalem": r.get("kalem"),
                      "is_no": r.get("is_no"), "tur": r.get("tur"), "olcu_mm": r.get("olcu_mm"),
                      "deneme": int(r.get("deneme") or 0), "gorulen": r.get("guncel") or "",
                      "urunler": r.get("urunler") or ""})
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


def girdi_hazirla(i, t, dizin):
    """Girdi dizinini kurar. Donus "" = hazir, aksi red sebebi. Erisim hatasi Erisilemedi."""
    if i["kuyruk"] == "siparis":
        g = siparis_girdisi(i, t)
        if g is None:
            return "kalem-yok"
        if not r2_al("foto-onizleme/%s.png" % i["is_no"], os.path.join(dizin, "gri_harita.png")):
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


# ------------------------------------------------------------------ uretec cagrisi (sozlesme §1)
def cli_tablosu():
    tablo = {k: dict(v) for k, v in URETEC_CLI.items()}
    ek = os.environ.get("FOTO_KOSUCU_URETEC_TABLO", "")
    if ek:
        with open(ek, encoding="utf-8") as f:
            tablo.update(json.load(f))
    return tablo


def uretec_kos(i, girdi_dizin, cikti):
    """Donus (rc, stderr ozeti). rc 0 ise cikti dizininde §3 dosyalari olmalidir."""
    g = cli_tablosu().get(i["uretec"])
    if not g:
        return 2, "RED uretec-tanimsiz"
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    ham = None
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
    if not all(isinstance(k.get(e), (int, float)) and 0 < k[e] <= PLAKA_MM for e in ("x", "y")):
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
        rc, ozet = (2, "RED " + sebep) if sebep else uretec_kos(i, girdi_dizin, cikti)
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
        yaz("%s %s%s" % (karar.upper(), is_adi(i), (" sebep=" + sebep) if sebep else "")
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
    yol = os.environ.get("FOTO_KOSUCU_KILIT") or os.path.join(tempfile.gettempdir(), "pruvo-foto-kosucu.kilit")
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
    ap.add_argument("--donustur-litofan", nargs=3, metavar=("HAM", "CIKTI", "GIRDI"), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.donustur_litofan:
        return donustur_litofan(*a.donustur_litofan)
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
