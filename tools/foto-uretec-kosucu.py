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
  yapboz   yapboz_uret             uzun_kenar_mm     form AYNEN (satir/sutun/tohum/kabartma_yon) palet renk1..4->renkler[0..3]
  anahtarlik isimlik_uret          genislik_mm       form AYNEN (satirlar listesi) +            plaka->renk_plaka
                                                     anahtarlik=true (kopru cagri.sabit)        yazi->renk_yazi
  anahtarlik_foto figur_kulak      (saglayici figuru) dosyalar.figur (3MF/STL) -> --girdi DOSYA; (tek govde, renk YOK)
                                                     figur_kulak_konum (tepe|sirt) -> konum -> kopru
                                                     `cagri.parametre_bayraklari` (--konum); yoksa tepe
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
import math
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
# OLCUM ARACI kanit dizini (--kanit-dizin; launchd VERMEZ -> ""): onarim figur kolunun ham ozet.json (kulak
# olcumleri) + onizleme.png kopyasi. D1/R2 sozlesmesine GIRMEZ (TUR-C2c, tools/foto-ornek-uc-uca.py --cesit figur).
KANIT_DIZIN = ""
SIPARIS_KALIBI = re.compile(r"^[A-Za-z0-9-]{6,40}$")  # shop/src/foto.js ile ayni
IS_KALIBI = re.compile(r"^[0-9a-f]{32}$")
# Uretec deposu SALT OKUNUR: alt surec __pycache__ yazmaz. `npx wrangler` alt surecleri de
# `~/.wrangler/logs`'a debug logu YAZMAZ (9 Eki: R2 put + D1 sorgu basina 1 dosya birikiyordu;
# gerekce + kaynak dogrulamasi `tools/d1-sync.py::WRANGLER_LOG_KAPALI`).
SALT_OKUMA_ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", WRANGLER_WRITE_LOGS="false")
DOSYA_ADI_KALIBI = re.compile(r"^[a-z_]{1,24}\.(png|jpg|jpeg|svg|wav|3mf|stl)$")
# ONARIM KAPISI (8 Eki 2026, BaBa hukmu): saglayici renk 3MF'i Worker'da `model.ham.3mf`e yazilir, satir
# 'onarim-bekliyor'a gecer; Worker ham dosyayi ASLA model.3mf yapmaz. Bu kosucu TeKiN koprusunu
# (`uc_mf_onar.py <ham> <cikti>`) kosar, `--olc <ham> <cikti>` rc 0 (acik/tekrarli/oz kenar 0 + manifold3d
# NoError + renk korunumu + olcek/hacim) gecerse cikti `model.3mf` olur ve satir 'hazir'; gecmezse 'elle'.
# Kopru yoksa is KUYRUKTA kalir (fail-closed: hazir yazilmaz). ④ bunu pruvo `uc_mf_olc` ile AYRICA olcer.
KOPRU_BETIK = "jeneratorler/foto/uc_mf_onar.py"
ONARIM_SURE_SN = 600

# KOMUT ESLEMESI — TEK YER: manifest `uretec` kimligi -> CLI. bicim "sozlesme" = §1 dogal cagri
# (`<komut> --girdi girdi.json --cikti <dizin>`); "litofan" = litofan_uret.py'nin kendi CLI'i
# (--girdi <gri png> --mm --ayak --cikti) + §3 donusumu (litofan.3mf/ozet.json -> model.3mf/olcu.json).
URETEC_CLI = {
    "litofan_uret": {"bicim": "litofan", "betik": "jeneratorler/foto/litofan_uret.py"},
    "isimlik_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/isimlik_uret.py", "esle": "isimlik"},
    # FOTO KOLU (anahtarlik-foto; 10 Eki figur_kulak, eski plaket_kulak eslemesi KALKTI): manifest `foto_kolu.uretec`;
    # `--girdi` JSON DEGIL figur DOSYASI, parametreler kopru `cagri.parametre_bayraklari` ile CLI bayragi
    # (dosya_girdisi = uretec girdisindeki dosya alani).
    "figur_kulak": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/figur_kulak.py", "esle": "anahtarlik_foto",
                    "kol": "foto", "dosya_girdisi": "figur"},
    "qr_plaket_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/qr_plaket_uret.py", "esle": "qr"},
    "svg_ekstruzyon_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/svg_ekstruzyon_uret.py",
                            "esle": "logo"},
    "muhur_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/muhur_uret.py", "esle": "muhur"},
    "siluet_sablon_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/siluet_sablon_uret.py",
                           "esle": "sablon"},
    "yapboz_uret": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/yapboz_uret.py", "esle": "yapboz"},
    "ozel_uret:kutu": {"bicim": "tekin-ortak", "betik": "jeneratorler/ozel_g4/ozel_uret.py", "esle": "kutu", "bayraklar": ["--tur", "kutu"]},
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
    "plaka_mm:k.PRUVO_FOTO.PLAKA_MM,cesitler:k.PRUVO_FOTO.cesitler}));"
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


def cesit_kaydi(tur, kod):
    """Manifest `cesitler` (VERI.cesitKaydi ile AYNI): turun `kod` cesidi; yoksa {}."""
    k = (_manifest_ham().get("cesitler") or {}).get(tur) or {}
    return next((c for c in k.get("secenekler") or [] if isinstance(c, dict) and c.get("kod") == kod), {})


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
    # Onarim kuyrugu siparis kalemini de okur (figur kolu `foto_renk_modu`: Renkli -> palet; RENK=PALET B).
    sat, _ = d1("SELECT u.siparis_no, u.kalem, u.is_no, u.tur, u.olcu_mm, u.deneme, u.guncel, s.urunler"
                " FROM foto_uretim u LEFT JOIN siparisler s ON s.siparis_no = u.siparis_no"
                " WHERE u.asama = 'onarim-bekliyor' ORDER BY u.tarih LIMIT " + str(IS_SINIRI))
    for r in sat:
        isler.append({"kuyruk": "onarim", "siparis_no": r.get("siparis_no"), "kalem": r.get("kalem"),
                      "is_no": r.get("is_no"), "tur": r.get("tur"), "olcu_mm": r.get("olcu_mm"),
                      "deneme": int(r.get("deneme") or 0), "gorulen": r.get("guncel") or "",
                      "urunler": r.get("urunler") or ""})
    for i in isler:
        t = manifest.get(i["tur"]) or {}
        i["motor"] = t.get("motor", "")
        i["uretec"] = t.get("uretec", "")
    return isler


def satirli(i):
    """foto_uretim satiri (siparis + onarim kuyrugu): kimlik siparis_no+kalem, CAS jetonu `guncel`."""
    return i["kuyruk"] in ("siparis", "onarim")


def is_adi(i):
    if satirli(i):
        return "%s %s#%s" % (i["kuyruk"], i["siparis_no"], i["kalem"])
    return "onizleme %s" % i["is_no"]


def cikti_anahtarlari(i):
    if satirli(i):
        d = "foto/%s/%s/" % (i["siparis_no"], i["kalem"])
    else:
        d = "foto-uretec-onizleme/%s/" % i["is_no"]
    return {ad: d + ad for ad in CIKTI_DOSYALARI}


def kimlik_gecerli(i):
    if not IS_KALIBI.match(str(i.get("is_no") or "")):
        return False
    if satirli(i):
        return bool(SIPARIS_KALIBI.match(str(i.get("siparis_no") or ""))) and isinstance(i.get("kalem"), int)
    return True


def nerede(i):
    if satirli(i):
        asama = "onarim-bekliyor" if i["kuyruk"] == "onarim" else "uretec-bekliyor"
        return ("foto_uretim", "siparis_no = %s AND kalem = %d AND asama = '%s'"
                % (sql_metin(i["siparis_no"]), i["kalem"], asama))
    return ("foto_isler", "is_no = %s AND asama = 'uretec-onizleme'" % sql_metin(i["is_no"]))


def jeton_kosulu(i, jeton):
    if satirli(i):
        return "guncel = %s" % sql_metin(jeton)
    return "son_kontrol = %d" % int(jeton)


def yeni_jeton(i):
    if satirli(i):
        j = simdi_iso()
        return j if j != i["gorulen"] else j + "~"
    return max(int(time.time() * 1000), int(i["gorulen"]) + 1)


def sonuc_sql(i, jeton, karar, sebep="", olcu=None):
    """karar: hazir | elle | ariza. Son yazim jetona bagli (CAS). `olcu` (yalniz onizleme + hazir):
    TURETILMIS eksenli turde onizlemede OLCULEN uzun kenar (tam mm) satirin olcu_mm'sine yazilir —
    sunucu fiyati ORADAN hesaplar (shop/src/foto.js uretecDurumYaniti / fotoKalemFiyatla)."""
    tablo, kosul = nerede(i)
    kosul += " AND " + jeton_kosulu(i, jeton)
    simdi = simdi_iso()
    if satirli(i):
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
            if olcu is not None:
                st += ", olcu_mm = %d" % int(olcu)
        elif karar == "elle":
            st = "asama = 'basarisiz', hata = %s, son_kontrol = %d" % (sql_metin(sebep), ms)
        else:
            st = "hata = %s, son_kontrol = %d" % (sql_metin("uretec-ariza-%d" % (i["deneme"] + 1)), ms)
    return "UPDATE %s SET %s WHERE %s" % (tablo, st, kosul)


def kirala_sql(i, jeton):
    tablo, kosul = nerede(i)
    alan = "guncel = %s" % sql_metin(jeton) if satirli(i) else "son_kontrol = %d" % int(jeton)
    return "UPDATE %s SET %s WHERE %s AND %s" % (tablo, alan, kosul, jeton_kosulu(i, i["gorulen"]))


def geri_ver_sql(i, jeton):
    tablo, kosul = nerede(i)
    alan = ("guncel = %s" % sql_metin(i["gorulen"]) if satirli(i)
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


RENK_MODU_SECENEK = ("tek", "palet")


def foto_renk_modu(i):
    """Figur kolunun uretim renk modu: siparis kaleminin `foto_renk_modu` (shop/src/foto.js; Renkli -> palet).
    Satir/kalem/alan yok, kalem baska ise ait ya da deger gecersiz -> "tek" (bugunku tek renk yolu AYNEN)."""
    k = siparis_kalemi(i.get("urunler"), i.get("kalem"))
    m = k.get("foto_renk_modu") if k and k.get("foto_is") == i.get("is_no") else None
    return m if m in RENK_MODU_SECENEK else "tek"


def siparis_girdisi(i, t):
    """shop/src/foto.js uretecGirdiJson'un AYNASI (kalem seciminden renk/malzeme)."""
    k = siparis_kalemi(i["urunler"], i["kalem"])
    if not k or k.get("foto_is") != i["is_no"]:
        return None
    sc = k.get("foto_secim") if isinstance(k.get("foto_secim"), dict) else {}
    renkler, malzemeler = {}, {}
    # Palet turunu deterministik uretec basiyorsa (bust) odenen renkler bolgelere sirayla: renkler[i] -> palet_bolgeleri[i]
    # (shop/src/foto.js VERI.paletBolgeRenkleri AYNASI).
    pr = k.get("foto_renkler") if isinstance(k.get("foto_renkler"), list) else []
    for b, r in zip(t.get("palet_bolgeleri") or [], pr):
        renkler[b] = r
    for b in t.get("renk_bolgeleri") or []:
        if sc.get(b.get("kod", "") + "_renk"):
            renkler[b["kod"]] = sc[b["kod"] + "_renk"]
    for b in (t.get("malzemeler") or {}):
        if sc.get(b + "_malzeme"):
            malzemeler[b] = sc[b + "_malzeme"]
    return {"sozlesme": 1, "kategori": i["tur"], "siparis_no": i["siparis_no"], "kalem": i["kalem"],
            # TURETILMIS eksen: onizleme girdisiyle AYNI (olcu 0; uretec olcuyu parametreden turetir) -> kopya kolu.
            "olcu_mm": 0 if turetilmis(t) else i["olcu_mm"], "renkler": renkler, "malzemeler": malzemeler,
            "parametreler": k.get("parametreler") if isinstance(k.get("parametreler"), dict) else {},
            "dosyalar": {"gri_harita": "gri_harita.png"}}


def ornek_girdisi(i, dizin, t):
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
        # TURETILMIS eksen: onizleme girdisi olcu 0 ile yazilir (surgu yok); siparisin olcu_mm'si OLCULEN deger.
        beklenen = 0 if turetilmis(t) else i["olcu_mm"]
        if (not isinstance(g, dict) or g.get("kategori") != i["tur"] or g.get("olcu_mm") != beklenen or
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
        return ornek_girdisi(i, dizin, t)
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


def _esle_gelen(g, dizin, rh):
    """G4 (ozel_uret) — YALNIZ gelen parametreler gecer (varsayilan enjeksiyonu YOK: eksik alan = uretecin
    kendi varsayilani). Sema/kosul/aralik denetimi VERI.parametreDogrula'da (sunucu) ve tekin_kos'ta (sema
    disi anahtar RED); koşulu saglanmayan alan buraya hic gelmez. Renk bolgesi yok."""
    return dict(g.get("parametreler") or {}), []


esle_kutu = esle_saksi = _esle_gelen


def esle_rolyef(g, dizin, rh):
    p = g.get("parametreler") or {}
    ad = (g.get("dosyalar") or {}).get("foto")
    if not isinstance(ad, str) or not os.path.isfile(os.path.join(dizin, ad)):
        raise KopruRed("gorsel")
    u = {"gorsel": os.path.join(os.path.abspath(dizin), ad),
         "uzun_kenar_mm": float(g["olcu_mm"]),
         "rolyef_yuksekligi_mm": float(p.get("rolyef_yuksekligi_mm", 3.0)),
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
    # Ses girdisi = form parametresi `genlik` (tip "ses": 64..4000 eleman, VERI.parametreDogrula);
    # yoksa eski yol (dosyalar.ses WAV).
    if isinstance(p.get("genlik"), list) and p["genlik"]:
        u = {"genlik": [float(x) for x in p["genlik"]]}
    else:
        ad = (g.get("dosyalar") or {}).get("ses")
        if not isinstance(ad, str) or not os.path.isfile(os.path.join(dizin, ad)):
            raise KopruRed("girdi-yok")
        u = {"wav": os.path.join(os.path.abspath(dizin), ad)}
    u.update({"uzun_kenar_mm": float(g["olcu_mm"]),
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
         "renk_yazi": _renk(g, "yazi", rh) or ""})
    # Baslik doluysa uretec ayri "yazi" govdesini renk_yazi ile basar (ses_dalgasi_uret) -> odenen yazi rengi parcada.
    return u, ["plaka", "cubuk"] + (["yazi"] if str(u.get("baslik") or "").strip() else [])

def esle_braille(g, dizin, rh):
    """kopru-15 ESLE: gelen parametreler (sunucu dogruladi; adlar kayitla AYNI) + olcu ekseni. Kayitta
    `olcek.belirleyen_parametre` = genislik_mm (0=oto) -> surgu (olcu_mm) hedef genislik. (Eski esleme
    `uzun_kenar_mm` gonderiyordu -> uretec `RET: bilinmeyen alan`; buyuk_harf bool -> enum disi.)"""
    p = g.get("parametreler") or {}
    m = p.get("metin", "")
    if not isinstance(m, str) or not m.strip():
        raise KopruRed("parametre")
    u = dict(p)  # braille
    u["genislik_mm"] = float(g["olcu_mm"])
    u["renk_plaka"] = _renk(g, "plaka", rh) or "#1A1A1A"
    u["renk_nokta"] = _renk(g, "nokta", rh) or "#E8E4D8"
    u["renk_yazi"] = _renk(g, "yazi", rh) or ""
    # Ust yazi doluysa uretec ayri "yazi" govdesini renk_yazi ile basar (braille_uret) -> odenen yazi rengi parcada.
    return u, ["plaka", "nokta"] + (["yazi"] if str(u.get("ust_yazi") or "").strip() else [])

# G5 sabit olcu ekseni: kaydin `olcek.belirleyen_parametre`si (kopru-esle-kapisi-test E3 kayittan olcer).
G5_OLCU_ALANI = {"topo": "olcu_mm", "sehir": "olcu_mm", "yildiz": "olcu_mm", "koordinat": "genislik_mm",
                 "anahtarlik": "genislik_mm"}
# Kayitta min 0 / varsayilan 0 (= "oto"/uretec varsayilani) ama uretec SEMA'si 0'i REDDEDER (kadir_esigi min 2,
# 0 YALNIZ varsayilan; kose_yaricap_mm min 1) -> 0 gelirse alan GONDERILMEZ (uretec kendi varsayilanini koyar).
G5_SIFIR_VARSAYILAN = {"yildiz": ("kadir_esigi",), "koordinat": ("kose_yaricap_mm",)}


def _esle_gelen_renkli(g, rh, kod):
    """G5 — YALNIZ gelen parametreler + secilen bolge renkleri `renk_<bolge>` (bolge adlari MANIFESTIN
    renk_bolgeleri'nden; kopru-manifest-uret.py onlari kaydin `renk_<b>` parametrelerinden turetir ->
    ad uretecle hizali). Manifestte olmayan bolgeye renk -> RED renk. Secilmeyen bolge = uretec varsayilani.
    Surgu olcusu (zarf olcu_mm) belirleyen alana YAZILIR (sabit eksen: fiyat surguden; uretec varsayilani DEGIL)."""
    bolgeler = [b.get("kod") for b in (manifest_oku().get(kod) or {}).get("renk_bolgeleri") or []]
    if any(b not in bolgeler for b in (g.get("renkler") or {})):
        raise KopruRed("renk")
    u = dict(g.get("parametreler") or {})
    u[G5_OLCU_ALANI[kod]] = float(g["olcu_mm"])
    for a in G5_SIFIR_VARSAYILAN.get(kod, ()):
        if u.get(a) == 0:
            del u[a]
    for b in bolgeler:
        h = _renk(g, b, rh)
        if h is not None:
            u["renk_" + b] = h
    return u, bolgeler


def esle_topo(g, dizin, rh):
    return _esle_gelen_renkli(g, rh, "topo")


def esle_sehir(g, dizin, rh):
    return _esle_gelen_renkli(g, rh, "sehir")


def esle_yildiz(g, dizin, rh):
    u, bolgeler = _esle_gelen_renkli(g, rh, "yildiz")
    # Uretec SEMA'sinda alt_yazi = liste (<= 2 satir); form alani tek satir metin -> tek ogeli liste.
    if isinstance(u.get("alt_yazi"), str):
        u["alt_yazi"] = [u["alt_yazi"]] if u["alt_yazi"].strip() else []
    return u, bolgeler


def esle_koordinat(g, dizin, rh):
    return _esle_gelen_renkli(g, rh, "koordinat")


def esle_bust(g, dizin, rh):
    """bust = rolyef ureteci + teklif alanlari; renk PALETTEN (manifest palet_bolgeleri: taban, rolyef). Odenen renkler
    sirayla bolgelere gelir (siparis_girdisi); 2 renk odendiyse uretec IKI RENKLI basar (iki_renk zorlanir — odenen
    renk basilir, BaBa 8 Eki 15:5x), tek renkte iki_renk KAPALI (odenmeyen ikinci renk basilmaz). Renk secilmemis
    (eski siparis) -> uretec varsayilani, bolge listesi bos."""
    u, _ = esle_rolyef(g, dizin, rh)
    secilen = [b for b in ("taban", "rolyef") if (g.get("renkler") or {}).get(b)]
    u["iki_renk"] = "rolyef" in secilen
    return u, (["taban", "rolyef"] if u["iki_renk"] else secilen)


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
    """yapboz (TeKiN kopru kaydi, K3c): form alanlari AYNEN + surgu olcusu uzun_kenar_mm'ye; renk PALETTEN: odenen
    renkler sirayla palet_bolgeleri'ne gelir (siparis_girdisi / VERI.paletBolgeRenkleri) ve uretecin `renkler`
    LISTESINE AYNI sirayla gecer (parca renkleri). Palet disi bolge ya da sira boslugu (renk2 var, renk1 yok) -> RED
    renk (odenen renk sessizce dusmez); renk yok -> uretec varsayilani."""
    pb = (manifest_oku().get("yapboz") or {}).get("palet_bolgeleri") or []
    if any(b not in pb for b in (g.get("renkler") or {})):
        raise KopruRed("renk")
    u = dict(g.get("parametreler") or {})
    u["gorsel"] = _gorsel(g, dizin)
    u["uzun_kenar_mm"] = float(g["olcu_mm"])
    secilen, renkler = [], []
    for b in pb:
        h = _renk(g, b, rh)
        if h is None:
            continue
        if len(secilen) != pb.index(b):
            raise KopruRed("renk")
        secilen.append(b)
        renkler.append(h)
    if renkler:
        u["renkler"] = renkler
    return u, secilen


def esle_anahtarlik(g, dizin, rh):
    """anahtarlik (TeKiN kopru kaydi, K3c) = isimlik_uret + kopru `cagri.sabit` {anahtarlik: true} (kulakli taban;
    plaka modunun yasak alanlari formda YOK). Form AYNEN (satirlar listesi VERI.parametreDogrula'dan), surgu olcusu
    genislik_mm'ye, secilen bolge renkleri renk_plaka / renk_yazi."""
    u, bolgeler = _esle_gelen_renkli(g, rh, "anahtarlik")
    u["anahtarlik"] = True
    return u, bolgeler


# figur_kulak kulakcik konumu (kopru FIGUR_KULAK_SEMA.konum); yazi kolunun `anahtarlik_kulak_konum`undan AYRI.
KONUM_VARSAYILAN = "tepe"
KONUM_SECENEK = ("tepe", "sirt")


def esle_anahtarlik_foto(g, dizin, rh):
    """anahtarlik FOTO kolu (TeKiN kopru kaydi `anahtarlik-foto`, figur_kulak; ② "Figur olarak"): girdi saglayicinin
    FIGUR turu ciktisi (`dosyalar.figur`, 3MF ya da STL), kulakcik konumu `figur_kulak_konum` (tepe|sirt; yoksa
    tepe). Renk bolgesi YOK (tek govde). Figur uzun kenari >72 mm ise uretec rc 2 -> `anahtarlik-boyut`
    (RET_KALIPLARI). Zarf `renk_modu` palet -> `--renk-modu palet` (3MF ucgen boyasi korunur); tek/yok -> bayrak
    YOK (komut bugunkuyle bayt-ayni)."""
    ad = (g.get("dosyalar") or {}).get("figur")
    if not isinstance(ad, str) or not DOSYA_ADI_KALIBI.match(ad) or not ad.endswith((".3mf", ".stl")) or \
            not os.path.isfile(os.path.join(dizin, ad)):
        raise KopruRed("gorsel")
    # Onarim kolu (figur_kos) konumu zarfin `konum`unda verir (K2 tepe -> sirt dususu; musteri formu degil).
    konum = (g.get("parametreler") or {}).get("figur_kulak_konum", g.get("konum") or KONUM_VARSAYILAN)
    if konum not in KONUM_SECENEK:
        raise KopruRed("parametre")
    u = {"figur": os.path.join(dizin, ad), "konum": konum}
    rm = g.get("renk_modu", "tek")
    if rm not in RENK_MODU_SECENEK:
        raise KopruRed("parametre")
    if rm == "palet":
        u["renk_modu"] = "palet"
    return u, []


def kopru_cagri(uretec):
    """Repodaki SABIT kopru kaydindan (jenerator/kopru/, TeKiN anlik goruntusu) uretecin `cagri`si; yoksa {}."""
    try:
        with open(os.path.join(KOK, "jenerator", "kopru", "kopru_kayitlari.json"), encoding="utf-8") as f:
            kayitlar = json.load(f).get("kayitlar") or []
    except (OSError, ValueError, AttributeError):
        return {}
    k = next((k for k in kayitlar if isinstance(k, dict) and k.get("uretec") == uretec), None)
    return (k or {}).get("cagri") or {}


def dosya_girdili_komut(g, u, py, jen, ham):
    """Dosya girdili uretec (figur_kulak): [betik] + bayraklar + parametre_bayraklari (kopru) + --girdi <dosya>.
    Kopru kaydi yoksa ya da parametre bayragi tanimsizsa None (fail-closed: uretec KOSMAZ)."""
    c = kopru_cagri(os.path.splitext(os.path.basename(g["betik"]))[0])
    pb = c.get("parametre_bayraklari")
    if c.get("betik") != g["betik"] or not isinstance(pb, dict):
        return None
    komut = [py, os.path.join(jen, g["betik"])] + list(c.get("bayraklar") or [])
    for ad in sorted(k for k in u if k != g["dosya_girdisi"]):
        if not isinstance(pb.get(ad), str):
            return None
        komut += [pb[ad], str(u[ad])]
    return komut + [c.get("girdi_bayragi") or "--girdi", u[g["dosya_girdisi"]],
                    c.get("cikti_bayragi") or "--cikti", ham]


# KATEGORI BASINA TEK esleme fonksiyonu (URETEC_CLI `esle` buradan secer).
ESLEMELER = {"isimlik": esle_isimlik, "qr": esle_qr, "logo": esle_logo, "muhur": esle_muhur,
             "sablon": esle_sablon, "yapboz": esle_yapboz, "anahtarlik": esle_anahtarlik,
             "anahtarlik_foto": esle_anahtarlik_foto,
             "kutu": esle_kutu,
             "saksi": esle_saksi,
             "rolyef": esle_rolyef,
             "ses": esle_ses,
             "braille": esle_braille,
             "topo": esle_topo,
             "sehir": esle_sehir,
             "yildiz": esle_yildiz,
             "koordinat": esle_koordinat,
             "bust": esle_bust}

# Uretec RET cumlesi -> red kodu (ilk eslesen; manifest URETEC_RED_METIN anahtari). Yok -> "genel".
RET_KALIPLARI = [
    # figur_kulak (anahtarlik foto kolu): figur >72 mm / kulak sigmadi -> TEK musteri cumlesi (Okan/BaBa birebir).
    (r"figur uzun kenar|kulak dahil uzun kenar|kulak yerlesmez", "anahtarlik-boyut"),
    (r"kontrast", "kontrast"),
    (r"parca kisa kenari|satir\*sutun|parca tabladan", "parca"),
    (r"metin cok uzun|modul boyutu", "qr-uzun"),
    (r"fontta bulunmayan|denetim/gorunmez|surrogate", "karakter"),
    # isimlik_uret anahtarlik kolu (genislik_mm) ince cizgi RET'i "yazi" icermez -> "metni kisalt" yazi reddidir
    # (Okan 10 Eki "onizleme yapilamiyor": 30 mm "Ayşe" -> eskiden ince-cizgi "gorsel dene" cumlesi).
    (r"yazi|satir|harf|metni kisalt", "metin-sigmadi"),
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


def min_hesapla(py, jen, kod, uretec_girdisi):
    """Kopru `min-hesapla` (TeKiN sozlesmesi): {"min_mm": <float>, "neden": ...} -> min_mm; yanit yok/bozuk -> None
    (fail-closed: cagiran onizlemeyi reddeder)."""
    try:
        p = subprocess.run([py, os.path.join(jen, "jeneratorler", "kopru", "kopru_uret.py"), "min-hesapla",
                            "--kategori", kod, "--girdi-mh", uretec_girdisi], capture_output=True, text=True,
                           timeout=120, env=SALT_OKUMA_ENV, cwd=jen if os.path.isdir(jen) else None)
        v = json.loads((p.stdout or "").strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None
    m = v.get("min_mm") if isinstance(v, dict) else None
    return float(m) if isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0 else None


def min_adim(t, mm):
    """Hesaplanan min'in surgu adimina yukari yuvarlanmisi (musteriye soylenen + sunucunun reddettigi sinir)."""
    a = (t.get("fiyat") or {}).get("adim_mm") or 1
    return int(math.ceil(mm / a - 1e-9) * a)


def esle_fonksiyonu(t, g):
    """Uretim yolunun esleme fonksiyonu — TEK secim noktasi (kopru-esle-kapisi-test + renk-esleme-test AYNISINI
    cagirir). Turun KENDI eslemesi once (bust rolyef_uret'i kosar ama palet renklerini esle_bust baglar; 8 Eki
    yerel 3MF olcumu: uretecin `esle`i secilince bust 2 renk odenip TEK extruder basiliyordu), yoksa uretecinki."""
    # FOTO KOLU (URETEC_CLI `kol: foto`): ayni turun ikinci uretecinin eslemesi turunkinden ONCE.
    if (g or {}).get("kol") == "foto":
        return ESLEMELER.get(g.get("esle"))
    return ESLEMELER.get((t or {}).get("kod")) or ESLEMELER.get((g or {}).get("esle"))


# ⑧ (10 Eki): eski bust/yapboz isinin form alani `uzun_kenar_mm` / `iki_renk` YOK SAYILIR (hata vermez). Olcu TEK
# kaynak zarfin olcu_mm'si (esle_rolyef/esle_yapboz yazar); bust iki_renk'i odenen renklerden kurar (esle_bust).
ESKI_ALANLAR = {"bust": ("uzun_kenar_mm", "iki_renk"), "yapboz": ("uzun_kenar_mm", "iki_renk")}


def eski_alanlari_at(kod, girdi):
    p = girdi.get("parametreler")
    if isinstance(p, dict) and ESKI_ALANLAR.get(kod):
        girdi["parametreler"] = {k: v for k, v in p.items() if k not in ESKI_ALANLAR[kod]}
    return girdi


def tekin_kos(g, t, girdi_dizin, cikti, py, jen):
    """§2 zarfi -> uretecin kendi JSON'u -> uretec -> §3 donusumu. Donus (rc, ozet)."""
    with open(os.path.join(girdi_dizin, "girdi.json"), encoding="utf-8") as f:
        girdi = json.load(f)
    eski_alanlari_at(t.get("kod"), girdi)
    fn = esle_fonksiyonu(t, g)
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
    kopru_veri = {"bolgeler": bolgeler}
    # DINAMIK MIN (BaBa 14:3x; TeKiN 6320f2a KOPRU-SEMA "Dinamik min_mm"): icerige bagli turde uretec KOSMADAN once
    # kopru `min-hesapla` sorulur; olcu altindaysa dürüst red `olcu-min-<N>` (musteri "bu icerik icin en az N mm"
    # gorur), ustundeyse min olcu.json'a yazilir (sunucu siparisi bu sinirin altinda 400 ile reddeder).
    if t.get("olcu_min_dinamik") is True:
        mh = min_hesapla(py, jen, t.get("kod"), ugirdi)
        if mh is None:
            return 2, "RED min-hesapla: kopru min-hesapla yaniti yok"
        kopru_veri["min_mm"] = mh
        olcu = girdi.get("olcu_mm")
        if isinstance(olcu, (int, float)) and not isinstance(olcu, bool) and 0 < olcu < mh:
            return 2, "RED olcu-min-%d: bu icerik icin en az %d mm" % (min_adim(t, mh), min_adim(t, mh))
    with open(kopru, "w", encoding="utf-8") as f:
        json.dump(kopru_veri, f)
    komut = [py, os.path.join(jen, g["betik"])] + list(g.get("bayraklar", []))
    if g.get("dosya_girdisi"):
        komut = dosya_girdili_komut(g, u, py, jen, ham)
        if komut is None:
            return 2, "RED parametre: kopru parametre_bayraklari yok"
    # 8 Eki 2026: G5 topo/sehir iki asamali (veri_cek.py --tur ... --girdi ... --cikti <veri.json>; ag:true)
    if g.get("on_adim"):
        oa = g["on_adim"]
        veri_yol = cikti + ".veri.json"
        oa_komut = [py, os.path.join(jen, oa["betik"])] + list(oa.get("bayraklar", []))
        # On adim (veri_cek.py) uretecin SEMA'siyla dogrular -> girdisi URETEC JSON'u (§2 zarfi DEGIL; zarf
        # verilince `RET: bilinmeyen alan: dosyalar, kategori, ...` -> topo/sehir ② uretec-red:on-adim).
        oa_komut += [oa["girdi_bayragi"], ugirdi, oa["cikti_bayragi"], veri_yol]
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
    if not g.get("dosya_girdisi"):
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


def boya_durumlari(s):
    """paint_color (BambuStudio/PrusaSlicer TriangleSelector) -> yaprak durumlari kumesi; bozuk dizge -> None.
    Onaltilik basamaklar TERS okunur; alt 2 bit bolunen kenar sayisi (0 = yaprak, aksi kenar+1 cocuk), yaprakta ust
    2 bit durum (3 -> sonraki basamak + 3, 15'ler birikir). Bos dizge = boyasiz ({0})."""
    try:
        b = [int(c, 16) for c in reversed(s)]
    except ValueError:
        return None
    k, bekleyen, durumlar = 0, 1, set()
    while bekleyen:
        if k >= len(b):
            return {0} if not b else None
        kod, k, bekleyen = b[k], k + 1, bekleyen - 1
        if kod & 3:
            bekleyen += (kod & 3) + 1
            continue
        d = kod >> 2
        if d == 3:
            while k < len(b) and b[k] == 15:
                d, k = d + 15, k + 1
            if k >= len(b):
                return None
            d, k = d + b[k], k + 1
        durumlar.add(d)
    return durumlar if k == len(b) else None


def uc_mf_extruder_sayisi(yol):
    """3MF'teki FARKLI extruder sayisi — OLCULUR; yoksa 0. Govde extruder'lari (Metadata/model_settings.config) +
    UCGEN BOYASI (RENK=PALET B: figur_kulak --renk-modu palet TEK govde yazar, renk ucgen basina `paint_color`'da;
    durum d>=1 -> extruder d, boyasiz ucgen/durum 0 -> govdenin extruder'i). Boya yoksa bugunku sayim AYNEN;
    bozuk boya dizgesi -> 0 (olculemedi)."""
    import zipfile
    try:
        with zipfile.ZipFile(yol) as z:
            s = z.read("Metadata/model_settings.config").decode("utf-8")
            modeller = [z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".model")]
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return 0
    govde = set(re.findall(r'key="extruder"\s+value="(\d+)"', s))
    boya, boyasiz = set(), False
    for m in modeller:
        for u in re.findall(r"<triangle\b[^>]*>", m):
            p = re.search(r'\bpaint_color="([^"]*)"', u)
            d = boya_durumlari(p.group(1)) if p else {0}
            if d is None:
                return 0
            boya |= {str(x) for x in d if x >= 1}
            boyasiz = boyasiz or 0 in d
    if not boya:
        return len(govde)
    return len(boya | (govde if boyasiz else set()))


def uc_mf_uzun_kenar(yol, oz, eksen=2):
    """Uzun kenar 3MF GEOMETRISINDEN olculur (ozetteki nominal degil; 7 Eki mimar karari 3): dunya
    koordinatinda (component + build donusumu) x/y kutusunun buyuk kenari (eksen=3: x/y/z — figur kulak
    dahil en uzun boyut). Parcalar tablada raf duzenindeyse (yapboz) ozet.parcalar[].tasima_mm cikarilarak
    BIRLESIK urun olculur. Geometri okunamazsa None (dogrulama uzun-kenar-tolerans ile duser)."""
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
    mn, mx = [float("inf")] * eksen, [float("-inf")] * eksen
    for b in re.finditer(r'<item\b[^>]*?objectid="(\d+)"(?:[^>]*?transform="([^"]*)")?', xml):
        ps = noktalar(b.group(1), b.group(2))
        tas = tasima.get(nesne.get(b.group(1), ("",))[0]) or [0.0, 0.0, 0.0]
        for p in ps:
            for i in range(eksen):
                mn[i] = min(mn[i], p[i] - tas[i])
                mx[i] = max(mx[i], p[i] - tas[i])
    if mn[0] == float("inf"):
        return None
    return max(mx[i] - mn[i] for i in range(eksen))


def donustur_tekin(ham, cikti, girdi_yolu, kopru_yolu):
    """tekin-ortak uretec ciktisi -> sozlesme §3 (uretec python'unda kosar; Pillow YALNIZ buyutmede)."""
    with open(girdi_yolu, encoding="utf-8") as f:
        girdi = json.load(f)
    with open(kopru_yolu, encoding="utf-8") as f:
        kv = json.load(f)
    bolgeler = kv.get("bolgeler") or []
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
    # Dinamik min (kopru min-hesapla) onizlemede olculduyse ozete: sunucu siparisi bu sinirin altinda reddeder.
    if isinstance(kv.get("min_mm"), (int, float)):
        olcu["min_mm"] = kv["min_mm"]
    with open(os.path.join(cikti, "olcu.json"), "w", encoding="utf-8") as f:
        json.dump(olcu, f, ensure_ascii=False, sort_keys=True)
    return 0


# ------------------------------------------------------------------ dogrulama (sozlesme §3)
def turetilmis(t):
    """Manifest `olcu_ekseni` (kopru-manifest-uret.py uretir): turetilmis -> surgu/hedef YOK, olcu OLCULUR."""
    return (t or {}).get("olcu_ekseni") == "turetilmis"


def olculen_mm(uk):
    """Olculen uzun kenar -> fiyatlanan tam mm (yarim yukari; foto-uretim-veri.js VERI.olculenMm ile AYNI)."""
    if isinstance(uk, bool) or not isinstance(uk, (int, float)) or not uk > 0:
        return None
    return int(math.floor(uk + 0.5))


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
    tu = turetilmis(t)
    uk = o.get("uzun_kenar_mm")
    # TURETILMIS eksen (kopru-15 dilim-3): hedef olcu YOK — olculen uzun kenar KAYITLI araliga duser mi;
    # aralik disi -> uretec reddi (musteri metni VERI.URETEC_RED_METIN["olcu-aralik-disi"]).
    if tu and not (olculen_mm(uk) is not None and a.get("en_az", 1) <= olculen_mm(uk) <= a.get("en_cok", 0)):
        return "uretec-red:olcu-aralik-disi"
    if not tu and not (isinstance(i["olcu_mm"], int) and a.get("en_az", 1) <= i["olcu_mm"] <= a.get("en_cok", 0)):
        return "olcu-aralik-disi"
    tol = TOLERANS.get(t.get("motor"))
    if not tol or not isinstance(uk, (int, float)) or (not tu and abs(uk - i["olcu_mm"]) > i["olcu_mm"] * tol + 1e-9):
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


def kopru_bul():
    """(python, kopru yolu). Kopru betigi yoksa Erisilemedi -> is KUYRUKTA kalir (hazir yazilmaz)."""
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    kopru = os.path.join(jen, KOPRU_BETIK)
    if not os.path.isfile(kopru):
        raise Erisilemedi("kopru-yok")
    return py, kopru


def d_kapisi(cikti):
    """Uretec (D/R) ciktisina AYNI onarim kapisi (BaBa 8 Eki: plaket/sehir dahil). Tek dosya `--olc` gecerse
    dokunulmaz; kirmiziysa kopru + cift `--olc` -> gecerse model.3mf onarilmisla degisir, olcu.json
    model_sha256 tazelenir. Donus sebep ("" = gecti). 8 Eki taramasi: 23/23 HAZIR ornek tek-dosya olcumden gecti."""
    py, kopru = kopru_bul()
    model = os.path.join(cikti, "model.3mf")
    try:
        p = subprocess.run([py, kopru, "--olc", model], capture_output=True, text=True, timeout=ONARIM_SURE_SN,
                           env=SALT_OKUMA_ENV)
    except (subprocess.TimeoutExpired, OSError):
        return "onarim-sure"
    if p.returncode == 0:
        return ""
    if p.returncode == 2:
        return "onarim-girdi-hatasi"
    ham = os.path.join(os.path.dirname(cikti), "model.ham.3mf")
    os.replace(model, ham)
    karar, sebep, _ = onarim_kapisi(ham, model)
    if karar != "hazir":
        return sebep or "onarim-kirmizi"
    olcu_yolu = os.path.join(cikti, "olcu.json")
    with open(olcu_yolu, encoding="utf-8") as f:
        olcu = json.load(f)
    with open(model, "rb") as f:
        olcu["model_sha256"] = hashlib.sha256(f.read()).hexdigest()
    with open(olcu_yolu, "w", encoding="utf-8") as f:
        json.dump(olcu, f, ensure_ascii=False, sort_keys=True)
    return ""


def onarim_kapisi(ham, cikti):
    """Kopru + kabul olcumu. Donus (karar, sebep, ozet); karar hazir | elle | ariza.
    Kopru betigi yoksa Erisilemedi -> is KUYRUKTA kalir (hazir yazilmaz)."""
    py, kopru = kopru_bul()

    def kos(arg):
        p = subprocess.run([py, kopru] + arg, capture_output=True, text=True, timeout=ONARIM_SURE_SN,
                           env=SALT_OKUMA_ENV)
        return p.returncode, ((p.stderr or "").strip().splitlines() or [""])[-1][:200], p.stdout

    try:
        rc, hata, _ = kos([ham, cikti])
        if rc == 2:
            return "elle", "onarim-girdi-hatasi", hata
        if rc != 0 or not os.path.isfile(cikti):
            return "elle", "onarim-kirmizi", "kopru rc=%d %s" % (rc, hata)
        rc, hata, cik = kos(["--olc", ham, cikti])
    except subprocess.TimeoutExpired:
        return "ariza", "onarim-sure", "sure-asimi"
    except OSError as e:
        return "ariza", "onarim-baslatilamadi", str(e)[:200]
    if rc != 0:
        try:
            kusur = json.loads(cik).get("kabul_kusurlari") or []
        except ValueError:
            kusur = [hata or "olcum-okunamadi"]
        return "elle", "onarim-kirmizi", "olc rc=%d %s" % (rc, ",".join(kusur)[:200])
    return "hazir", "", "olc rc=0"


def onarim_figur_ureteci(i, t, gecici):
    """FIGUR KOLU (TUR-C2a): onarim kuyrugundaki isin onizleme girdi.json'u (shop/src/foto.js onizlemeGonder).
    Dosya yok ya da `uretec` alani yok -> None (eski is: onarilmis model AYNEN teslim). `cesit=figur` ve `uretec`
    manifestin `foto_kolu.uretec`iyle AYNI -> uretec adi; aksi "" (fail-closed: 'elle' uretec-uyusmaz)."""
    oy = os.path.join(gecici, "onizleme-girdi.json")
    if not r2_al(ONIZLEME_DIZIN % i["is_no"] + "girdi.json", oy):
        return None
    try:
        with open(oy, encoding="utf-8") as f:
            g = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(g, dict) or "uretec" not in g:
        return None
    fk = t.get("foto_kolu") if isinstance(t.get("foto_kolu"), dict) else {}
    u = g.get("uretec")
    return u if g.get("cesit") == "figur" and isinstance(u, str) and u and u == fk.get("uretec") else ""


def _xml_ad(etiket):
    return etiket.rsplit("}", 1)[-1]


def _xml_yol(e):
    """Production uzantisi `p:path` (ad alani ne olursa olsun yerel adi `path`); yoksa None."""
    return next((v for k, v in e.attrib.items() if _xml_ad(k) == "path"), None)


def _matris(t):
    a = [float(x) for x in (t or "1 0 0 0 1 0 0 0 1 0 0 0").split()]
    if len(a) != 12 or not all(math.isfinite(x) for x in a):
        raise ValueError("transform bozuk")
    return a


def _matris_carp(ic, dis):
    """Once `ic` sonra `dis` uygulanan 3MF donusumu (satir vektoru: p' = p*M + T)."""
    m = [0.0] * 12
    for r in range(4):
        for c in range(3):
            m[r * 3 + c] = sum((ic[r * 3 + k] if r < 3 else ic[9 + k]) * dis[k * 3 + c] for k in range(3)) + \
                (dis[9 + c] if r == 3 else 0.0)
    return m


def figur_duzlestir(model, stl):
    """FIGUR KOLU 3MF OKUMA (TUR-C2d, mimar K1-b): onarilmis 3MF (Production `p:path` bilesenleri DAHIL) -> TEK govde
    ikili STL (dunya koordinati, min kose 0'a otelenmis; deterministik). figur_kulak Production bilesenini OKUYAMAZ
    (`3mf icinde mesh nesnesi yok`). Donus: None = yazildi; aksi hata metni (cagiran 'elle' uretec-red:genel). Birden
    cok mesh govdesi -> hata (sessiz birlestirme YOK)."""
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        z = zipfile.ZipFile(model)
    except (OSError, zipfile.BadZipFile) as e:
        return "3mf okunamadi: %s" % type(e).__name__
    with z:
        kok = "3D/3dmodel.model"
        try:
            rels = z.read("_rels/.rels").decode("utf-8")
            m = re.search(r'Target="/?([^"]+)"[^>]*Type="[^"]*3dmodel"|Type="[^"]*3dmodel"[^>]*Target="/?([^"]+)"', rels)
            kok = (m.group(1) or m.group(2)) if m else kok
        except (KeyError, UnicodeDecodeError):
            pass
        agaclar = {}

        def nesneler(yol):
            yol = yol.lstrip("/")
            if yol not in agaclar:
                try:
                    kokel = ET.fromstring(z.read(yol))
                except (KeyError, ET.ParseError):
                    raise ValueError("model parcasi okunamadi: " + yol)
                agaclar[yol] = ({e.get("id"): e for e in kokel.iter() if _xml_ad(e.tag) == "object"}, kokel)
            return agaclar[yol]

        govdeler = []

        def coz(yol, oid, mat, derinlik):
            if derinlik > 8:
                raise ValueError("bilesen derinligi > 8")
            nesne = nesneler(yol)[0].get(oid)
            if nesne is None:
                raise ValueError("nesne yok: %s#%s" % (yol, oid))
            for e in nesne:
                if _xml_ad(e.tag) == "mesh":
                    govdeler.append((e, mat))
                elif _xml_ad(e.tag) == "components":
                    for k in e:
                        if _xml_ad(k.tag) == "component":
                            coz(_xml_yol(k) or yol, k.get("objectid"), _matris_carp(_matris(k.get("transform")), mat),
                                derinlik + 1)

        try:
            for e in nesneler(kok)[1].iter():
                if _xml_ad(e.tag) == "item":
                    coz(_xml_yol(e) or kok, e.get("objectid"), _matris(e.get("transform")), 0)
            if len(govdeler) != 1:
                return ("figur cok govdeli (%d govde); tek govde gerekli" % len(govdeler)) if govdeler else \
                    "3mf icinde mesh nesnesi yok"
            mesh, mat = govdeler[0]
            v, u = [], []
            for e in mesh:
                if _xml_ad(e.tag) == "vertices":
                    for x in e:
                        p = (float(x.get("x")), float(x.get("y")), float(x.get("z")))
                        v.append(tuple(p[0] * mat[c] + p[1] * mat[3 + c] + p[2] * mat[6 + c] + mat[9 + c]
                                       for c in range(3)))
                elif _xml_ad(e.tag) == "triangles":
                    u = [(int(x.get("v1")), int(x.get("v2")), int(x.get("v3"))) for x in e]
        except (ValueError, TypeError) as e:
            return "3mf cozulemedi: %s" % e
    if not v or not u or any(not 0 <= k < len(v) for t in u for k in t) or \
            not all(math.isfinite(c) for p in v for c in p):
        return "3mf mesh bos ya da bozuk"
    alt = [min(p[c] for p in v) for c in range(3)]
    v = [tuple(p[c] - alt[c] for c in range(3)) for p in v]
    with open(stl, "wb") as f:
        f.write(b"PRUVO figur duz".ljust(80, b"\0") + struct.pack("<I", len(u)))
        for a, b, c in u:
            pa, pb, pc = v[a], v[b], v[c]
            e1, e2 = [pb[k] - pa[k] for k in range(3)], [pc[k] - pa[k] for k in range(3)]
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            ln = math.sqrt(sum(k * k for k in n)) or 1.0
            f.write(struct.pack("<12fH", *([k / ln for k in n] + list(pa) + list(pb) + list(pc) + [0])))
    return None


# K2 (TUR-C2d): once tepe; uretec `kulak yerlesmez (tepe)` ya da (BaBa 16:0x 2b, ONERI c) tepe konumunda
# `kulak dahil uzun kenar ... (konum=tepe` (291,6–300 dik figur: sirtta kulak uzun kenari buyutmez) ile reddederse
# AYNI iste bir kez sirt; musteriye konum/ret YOK. Baska ret sinifinda (XY uzun kenar, cok bilesen, ...) dusus YOK.
FIGUR_KONUM_SIRASI = ("tepe", "sirt")
TEPE_RED = re.compile(r"kulak yerlesmez \(tepe\)|kulak dahil uzun kenar [0-9.]+ mm > [0-9.]+ mm \(konum=tepe\b")
# FIGUR OLCU KURALI (B2, KraL 10 Eki; BaBa 14:0x "kulak dahil en uzun boyut", kopru 2950833): anahtarlik figur
# cesidinde surgu = kulakcik DAHIL en uzun boyut (3 eksen). Sunucu ciplak figuru siparis olcusune olcekler
# (foto-uretim-veri.js VERI.olcekHedefMm — kuralin TEK yeri); kulak sirtta ya da XY-uzun figurde uzun kenari
# BUYUTMEZ, tepede ancak sigarsa. Bu yuzden tepe ciktisinin kulak dahil uzun kenari olcu*(1+tolerans)'i asarsa
# AYNI iste sirt (K2 dususu bu duruma da genisler; musteriye konum secimi YOK). Son kabul: figur_olcu_kabul.
FIGUR_OLCU_TOLERANS = 0.03  # shop/src/foto.js OLCU_TOLERANS ile AYNI (saglayici olcegi bu toleransla gecer)


def figur_kulak_dahil_mm(cd):
    """Figur ureteci ciktisinin kulak dahil en uzun boyutu (model.3mf GEOMETRISINDEN, 3 eksen); okunamazsa None."""
    return uc_mf_uzun_kenar(os.path.join(cd, "model.3mf"), {}, eksen=3)


def figur_tepe_sigar(i, cd):
    """Tepe ciktisinin kulak dahil uzun kenari siparis olcusu (+tolerans) icinde mi (sigmazsa koşucu sirt dener)."""
    L = figur_kulak_dahil_mm(cd)
    return L is not None and L <= i["olcu_mm"] * (1 + FIGUR_OLCU_TOLERANS) + 1e-9


def figur_olcu_kabul(i, cd):
    """URETIM OLCUM KABULU (figur cesidi): siparis olcusu cesit araliginda (en_az..olcu_en_cok) VE kulak dahil
    uzun kenar = olcu (± FIGUR_OLCU_TOLERANS). Donus "" = gecer; aksi RED metni (cagiran 'elle' uretec-red:
    olcu-tutmadi; sessiz teslim YOK)."""
    L = figur_kulak_dahil_mm(cd)
    olcu = i["olcu_mm"]
    ck = cesit_kaydi(i["tur"], "figur")
    en_az = max(((manifest_oku().get(i["tur"]) or {}).get("olcu_mm") or {}).get("en_az", 1), ck.get("olcu_en_az") or 0)
    en_cok = ck.get("olcu_en_cok", 0)
    if L is None or not (isinstance(olcu, int) and en_az <= olcu <= en_cok) or \
            abs(L - olcu) > olcu * FIGUR_OLCU_TOLERANS + 1e-9:
        return "RED olcu-tutmadi: kulak dahil %s mm, siparis %s mm (aralik %s..%s)" % (
            "?" if L is None else "%.2f" % L, olcu, en_az, en_cok)
    return ""


def figur_kos(i, t, uretec, model, gecici):
    """Onarilmis figur -> duz STL (figur_duzlestir) -> cesidin ureteci (figur_kulak): zarf dosyalar.figur=figur.stl,
    zarf `konum` (FIGUR_KONUM_SIRASI; tepe reddi ya da tepe olcuye sigmadi -> sirt), sonra figur_olcu_kabul.
    PALET (siparis Renkli, foto_renk_modu): STL ucgen boyasini SILER -> onarilmis 3MF AYNEN figur.3mf + zarf
    renk_modu palet (uretec --renk-modu palet). Donus (rc, ozet, uretilen model.3mf yolu, konum)."""
    gd = os.path.join(gecici, "figur-girdi")
    os.makedirs(gd)
    palet = foto_renk_modu(i) == "palet"
    figur = "figur.3mf" if palet else "figur.stl"
    if palet:
        shutil.copyfile(model, os.path.join(gd, figur))
        hata = ""
    else:
        hata = figur_duzlestir(model, os.path.join(gd, "figur.stl"))
    if hata:
        return 2, "RED genel: " + hata, os.path.join(gecici, "figur-yok", "model.3mf"), ""
    i["uretec"] = uretec
    for konum in FIGUR_KONUM_SIRASI:
        cd = os.path.join(gecici, "figur-cikti-" + konum)
        zarf = {"sozlesme": 1, "kategori": i["tur"], "siparis_no": i["siparis_no"], "kalem": i["kalem"],
                "olcu_mm": i["olcu_mm"], "dosyalar": {"figur": figur}, "parametreler": {}, "konum": konum}
        if palet:
            zarf["renk_modu"] = "palet"
        with open(os.path.join(gd, "girdi.json"), "w", encoding="utf-8") as f:
            json.dump(zarf, f)
        rc, ozet = uretec_kos(i, gd, cd, t)
        if rc == 0 and konum != FIGUR_KONUM_SIRASI[-1] and not figur_tepe_sigar(i, cd):
            continue
        if not (rc == 2 and TEPE_RED.search(ozet)):
            break
    if rc == 0:
        red = figur_olcu_kabul(i, cd)
        if red:
            rc, ozet = 2, red
    return rc, ozet, os.path.join(cd, "model.3mf"), konum


def kanit_yaz(i, cd):
    """--kanit-dizin verildiyse figur ureteci ciktisi (<cd>.ham/ozet.json + <cd>/onizleme.png) -> <dizin>/<siparis_no>/.
    Kopya hatasi isin kararini DEGISTIRMEZ (olcum araci eksik dosyayi kendisi EKSIK sayar)."""
    if not KANIT_DIZIN:
        return
    hedef = os.path.join(KANIT_DIZIN, i["siparis_no"])
    try:
        os.makedirs(hedef, exist_ok=True)
        for kaynak in (os.path.join(cd + ".ham", "ozet.json"), os.path.join(cd, "onizleme.png")):
            if os.path.isfile(kaynak):
                shutil.copyfile(kaynak, os.path.join(hedef, os.path.basename(kaynak)))
    except OSError:
        pass


def onarim_isle(i, jeton, yaz, t=None):
    """'onarim-bekliyor' satiri: R2 model.ham.3mf -> kopru -> olcum -> model.3mf + 'hazir' (ya da 'elle').
    Figur cesidi (onizleme girdi.json `uretec`): onarilmis model cesidin ureteciyle (figur_kulak) islenir."""
    d = "foto/%s/%s/" % (i["siparis_no"], i["kalem"])
    gecici = tempfile.mkdtemp(prefix="foto-onarim-")
    try:
        ham, cikti = os.path.join(gecici, "ham.3mf"), os.path.join(gecici, "model.3mf")
        if not r2_al(d + "model.ham.3mf", ham):
            karar, sebep, ozet = "elle", "onarim-ham-yok", ""
        else:
            karar, sebep, ozet = onarim_kapisi(ham, cikti)
        fu = onarim_figur_ureteci(i, t or {}, gecici) if karar == "hazir" else None
        if fu == "":
            karar, sebep = "elle", "uretec-uyusmaz"
        elif fu:
            rc, fozet, cikti, konum = figur_kos(i, t or {}, fu, cikti, gecici)
            if rc == 0:
                kanit_yaz(i, os.path.dirname(cikti))
            if rc == 2:
                karar, sebep = "elle", red_sebebi(fozet)
            elif rc != 0:
                karar, sebep = "ariza", "uretec-ariza"
            # renk = uretilen model.3mf'in OLCULEN extruder sayisi (palet siparisinde renk korunumu kaniti).
            ozet = (ozet + " " if ozet else "") + "uretec=" + fu + (" konum=" + konum if konum else "") + \
                (" renk_modu=%s renk=%d" % (foto_renk_modu(i), uc_mf_extruder_sayisi(cikti)) if rc == 0 else
                 " rc=%s %s" % (rc, fozet))
        if karar == "ariza" and i["deneme"] + 1 >= DENEME_TAVANI:
            karar = "elle"
        if karar == "hazir":
            r2_koy(d + "model.3mf", cikti, "model/3mf")
        _, n = d1(sonuc_sql(i, jeton, karar, sebep))
        if n != 1:
            yaz("CAS %s son yazim tutmadi (jeton degismis)" % is_adi(i))
            return "cas"
        yaz("%s %s%s %s" % (karar.upper(), is_adi(i), (" sebep=" + sebep) if sebep else "", ozet))
        return {"hazir": "uretildi", "elle": "red", "ariza": "ariza"}[karar]
    except Erisilemedi:
        try:
            d1(geri_ver_sql(i, jeton))  # onarim kuyrugu: kira geri (kopru/R2/D1 yok -> is kuyrukta)
        except Erisilemedi:
            pass
        raise
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def plan_bas(i, yaz):
    a = cikti_anahtarlari(i)
    yaz("IS %s tur=%s olcu=%s motor=%s uretec=%s deneme=%d"
        % (is_adi(i), i["tur"], i["olcu_mm"], i["motor"] or "-", i["uretec"] or "-", i["deneme"]))
    if i["kuyruk"] == "onarim":
        yaz("  PLAN KOPRU %s -> %s" % (a["model.3mf"].replace("model.3mf", "model.ham.3mf"), a["model.3mf"]))
        yaz("  PLAN D1 %s" % sonuc_sql(i, "<jeton>", "hazir"))
        return
    for ad in CIKTI_DOSYALARI:
        yaz("  PLAN R2 PUT %s/%s" % (R2_KOVA, a[ad]))
    yaz("  PLAN D1 %s" % sonuc_sql(i, "<jeton>" if satirli(i) else 0, "hazir"))


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
    if i["kuyruk"] == "onarim":
        return onarim_isle(i, jeton, yaz, t)
    gecici = tempfile.mkdtemp(prefix="foto-kosucu-")
    try:
        girdi_dizin = os.path.join(gecici, "girdi")
        os.makedirs(girdi_dizin)
        cikti = os.path.join(gecici, "cikti")
        olcu_yaz = None
        sebep = girdi_hazirla(i, t, girdi_dizin) if t.get("motor") in TOLERANS else "kol-uygun-degil"
        if sebep:
            rc, ozet = 2, "RED " + sebep
        else:
            sha = kanonik_girdi_sha(girdi_dizin)
            rc, ozet = onizleme_kopyala(i, sha, cikti) or uretec_kos(i, girdi_dizin, cikti, t)
            if rc == 0:
                girdi_sha_damgala(cikti, sha)
        if rc == 0:
            sebep = cikti_dogrula(i, t, cikti) or d_kapisi(cikti)
            if not sebep:
                a = cikti_anahtarlari(i)
                tur = {"model.3mf": "model/3mf", "olcu.json": "application/json", "onizleme.png": "image/png"}
                for ad in CIKTI_DOSYALARI:
                    r2_koy(a[ad], os.path.join(cikti, ad), tur[ad])
                karar = "hazir"
                if turetilmis(t) and i["kuyruk"] != "siparis":
                    with open(os.path.join(cikti, "olcu.json"), encoding="utf-8") as f:
                        olcu_yaz = olculen_mm(json.load(f).get("uzun_kenar_mm"))
            else:
                karar = "elle"
        elif rc == 2:
            sebep = sebep or red_sebebi(ozet)
            karar = "elle"
        else:
            karar = "elle" if i["deneme"] + 1 >= DENEME_TAVANI else "ariza"
            sebep = "uretec-ariza"
        _, n = d1(sonuc_sql(i, jeton, karar, sebep, olcu_yaz if karar == "hazir" else None))
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


# SAGLIK DAMGASI (10 Eki 2026): her --uygula turunun SONUNDA (BOS dahil; OLCULEMEDI/KILITLI/KURU haric) hedef
# D1 foto_ayar.kosucu_son_tik = ISO zaman. /foto/durum `hazirlayici_yas_sn`'yi buradan turetir; damga bayatsa ④
# "sirada" ekrani hazirlayicinin cevrimdisi oldugunu soyler. Tablo/sutunlar shop/src/foto.js ayarYaz ile AYNI.
DAMGA_ANAHTAR = "kosucu_son_tik"


def damga_yaz(yaz):
    iso = simdi_iso()
    try:
        d1("INSERT INTO foto_ayar (anahtar, deger, guncel) VALUES ('%s', '%s', %d)"
           " ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger, guncel = excluded.guncel"
           % (DAMGA_ANAHTAR, iso, int(time.time() * 1000)))
    except Erisilemedi as e:
        yaz("DAMGA yazilamadi (%s) — ekran hazirlayiciyi cevrimdisi gosterir" % e)


def calistir(uygula, yaz):
    fd = kilit_al()
    if fd is None:
        return "HAL=KILITLI rc=3", 3
    try:
        satir, rc = tur_kos(uygula, yaz)
        if uygula and rc != 4:
            damga_yaz(yaz)
        return satir, rc
    finally:
        os.close(fd)


def tur_kos(uygula, yaz):
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Foto uretec kosucusu (varsayilan KURU)")
    ap.add_argument("--uygula", action="store_true", help="D1/R2'ye YAZ (yalniz launchd / mimar)")
    ap.add_argument("--log", help="ciktiyi bu dosyaya ekle (5 MB tavan, eskisi silinir)")
    ap.add_argument("--hedef", choices=["canli", "onizleme"], default="canli",
                    help="D1/R2 hedefi (onizleme: shop/wrangler.onizleme.toml; varsayilan canli)")
    ap.add_argument("--kanit-dizin", default="",
                    help="olcum araci: onarim figur kolu ozet.json + onizleme.png kopyasi <dizin>/<siparis_no>/")
    ap.add_argument("--donustur-litofan", nargs=3, metavar=("HAM", "CIKTI", "GIRDI"), help=argparse.SUPPRESS)
    ap.add_argument("--donustur-tekin", nargs=4, metavar=("HAM", "CIKTI", "GIRDI", "KOPRU"), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.donustur_litofan:
        return donustur_litofan(*a.donustur_litofan)
    if a.donustur_tekin:
        return donustur_tekin(*a.donustur_tekin)
    hedef_kur(a.hedef)
    global KANIT_DIZIN
    KANIT_DIZIN = a.kanit_dizin
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
