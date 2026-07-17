#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO YAZDIR — bir siparisin uretim dosyalarini indirir ve Bambu Studio'da acar.

    python3 tools/yazdir.py <siparis_no> [--sadece-indir] [--klasor <yol>] [--anahtar <k>] [--taban <url>]

Ne yapar (yerel, Okan'in makinesinde):
  1. Yonetim anahtarini (.yonet-anahtar / --anahtar / YONET_ANAHTAR) okur.
  2. Canli yonetim API'sinden (pruvo3d.com/api/shop/yonet) siparisi bulur.
  3. Her kalemin uretim dosyalarini indirir:
       - Normal urun  -> /stl-liste ile parca adlari, sonra parca basina /stl.
       - Sari/parametrik -> /stl?siparis_no=&kalem= (derleme SERVER-SIDE yapilir;
         worker ic-derle'yi IC_DERLE_ANAHTAR ile kendisi cagirir — istemci sadece
         X-Yonet-Anahtar tasir).
  4. Terminale buyuk/net BASKI FISI basar (MALZEME + RENK goze batar).
  5. --sadece-indir degilse dosyalari Bambu Studio'da acar (macOS `open -a`).

GUVENLIK:
  - Anahtar SADECE HTTP header'inda (X-Yonet-Anahtar) gider; URL'ye/loga/fise YAZILMAZ.
  - Cloudflare bot korumasi icin User-Agent: Mozilla/5.0 gonderilir (yoksa 403).
  - Musteri PII (tel/adres) fiste gosterilebilir (yerel arac). Kaynak/tedarikci/
    lisans bilgisi zaten uclarda YOK, gosterilmez.
  - Dosyasi olmayan kalem SESSIZCE atlanmaz: "dosya yok: <id>" satiri basilir.

Kabul: tools/yazdir-test.py (sahte API + sahte STL; canliya baglanmaz).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

VARSAYILAN_TABAN = "https://pruvo3d.com"
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (PRUVO yazdir.py)"
ZAMAN_ASIMI = 300  # saniye (buyuk STL'ler icin genis)

BAMBU_ADAYLARI = (
    "/Applications/Bambu Studio.app",
    os.path.expanduser("~/Applications/Bambu Studio.app"),
    "/Applications/BambuStudio.app",
)


# ----------------------------------------------------------------- anahtar

def _ana_repo_koku():
    """Worktree'den calisiyorsak ana calisma agacinin kokunu bulur (git).

    .yonet-anahtar gitignore'da ve yalniz ana repoda; worktree'de yok. Bu yuzden
    anahtar dosyasi worktree kokunde bulunamazsa ana repo koku denenir. Guvenli:
    git yoksa/patlarsa None doner, cagiran yer atlar.
    """
    try:
        p = subprocess.run(
            ["git", "-C", KOK, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True)
        d = (p.stdout or "").strip()
        # Worktree'de common-dir mutlak <ana>/.git yolunu verir; normal repoda ".git".
        if d and os.path.isabs(d) and os.path.basename(d) == ".git":
            return os.path.dirname(d)
    except Exception:
        pass
    return None


def anahtar_dosyalari():
    """Anahtar dosyasi icin aday yollar (once worktree/ana repo koku)."""
    adaylar = [os.path.join(KOK, ".yonet-anahtar")]
    ana = _ana_repo_koku()
    if ana:
        adaylar.append(os.path.join(ana, ".yonet-anahtar"))
    return adaylar


def anahtar_oku(cli_anahtar):
    """Anahtari cozer: --anahtar > YONET_ANAHTAR env > .yonet-anahtar dosyasi.

    Bulunamazsa None. Anahtar hicbir yere BASILMAZ.
    """
    if cli_anahtar and cli_anahtar.strip():
        return cli_anahtar.strip()
    env = os.environ.get("YONET_ANAHTAR")
    if env and env.strip():
        return env.strip()
    for yol in anahtar_dosyalari():
        try:
            if os.path.exists(yol):
                with open(yol, "r", encoding="utf-8") as f:
                    icerik = f.read().strip()
                if icerik:
                    return icerik
        except OSError:
            continue
    return None


# ----------------------------------------------------------------- http

def _istek(taban, yol, anahtar):
    url = taban.rstrip("/") + yol
    return urllib.request.Request(url, headers={
        "User-Agent": UA,
        "X-Yonet-Anahtar": anahtar,  # anahtar SADECE header'da
        "Accept": "*/*",
    })


def api_json(taban, yol, anahtar):
    """JSON ucu GET eder; (http_kod, obj) doner. Baglanti hatasinda (None, {...})."""
    try:
        with urllib.request.urlopen(_istek(taban, yol, anahtar), timeout=ZAMAN_ASIMI) as r:
            ham = r.read()
            try:
                return getattr(r, "status", 200) or 200, json.loads(ham.decode("utf-8"))
            except ValueError:
                return getattr(r, "status", 200) or 200, None
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None
    except urllib.error.URLError as e:
        return None, {"hata": "baglanti: %s" % e.reason}


def dosya_indir(taban, yol, anahtar, hedef_yol):
    """Tek dosyayi stream'leyerek indirir (buyuk STL guvenli). Sonuc dict:
        {"durum":"ok","boyut":N} | {"durum":"yok","not":s} | {"durum":"hata","not":s}
    HTTPError urlopen'da atilir -> hedef dosya OLUSTURULMAZ (kismi dosya kalmaz).
    """
    try:
        with urllib.request.urlopen(_istek(taban, yol, anahtar), timeout=ZAMAN_ASIMI) as r:
            ct = (r.headers.get("Content-Type") or "").lower()
            if "json" in ct:  # savunma: 200 ama JSON hata govdesi -> .stl'e yazma
                try:
                    j = json.loads(r.read().decode("utf-8"))
                except Exception:
                    j = {}
                return {"durum": "yok", "not": j.get("not") or j.get("hata") or "bos yanit"}
            toplam = 0
            with open(hedef_yol, "wb") as f:
                while True:
                    parca = r.read(65536)
                    if not parca:
                        break
                    f.write(parca)
                    toplam += len(parca)
            return {"durum": "ok", "boyut": toplam}
    except urllib.error.HTTPError as e:
        mesaj = ""
        try:
            j = json.loads(e.read().decode("utf-8"))
            mesaj = j.get("not") or j.get("hata") or ""
        except Exception:
            mesaj = ""
        return {"durum": "yok" if e.code == 404 else "hata", "kod": e.code, "not": mesaj}
    except urllib.error.URLError as e:
        return {"durum": "hata", "not": str(e.reason)}


# ----------------------------------------------------------------- yardimci

def guvenli_ad(ad):
    """Dosya adini path ayiracisiz/temiz hale getirir (traversal savunmasi)."""
    ad = os.path.basename(str(ad or "")).strip()
    ad = re.sub(r"[^A-Za-z0-9._-]", "_", ad)
    return ad or "parca"


def _q(s):
    return urllib.parse.quote(str(s or ""), safe="")


def siparis_bul(taban, anahtar, siparis_no):
    """Listeden siparisi bulur. (siparis|None, hata_mesaji|None)."""
    kod, obj = api_json(taban, "/api/shop/yonet/liste?limit=200", anahtar)
    if kod == 404:
        return None, "yonetim erisimi reddedildi (404) — anahtar yanlis ya da ozellik kapali."
    if kod != 200 or not isinstance(obj, dict):
        return None, "siparis listesi alinamadi (kod %s)." % kod
    for s in obj.get("siparisler") or []:
        if s.get("siparis_no") == siparis_no:
            return s, None
    return None, "siparis bulunamadi: %s (son 200 siparis icinde yok)." % siparis_no


def kalem_isle(taban, anahtar, siparis_no, kalem, klasor):
    """Bir kalemin dosyalarini indirir; sonuc dict (fis + acma icin)."""
    i = int(kalem.get("kalem", 0) or 0)
    sonuc = {
        "kalem": i,
        "id": kalem.get("id") or "",
        "baslik": kalem.get("baslik") or kalem.get("id") or "?",
        "malzeme": kalem.get("malzeme") or "-",
        "renk": kalem.get("renk") or "-",
        "adet": kalem.get("adet") or 1,
        "parametrik": bool(kalem.get("parametrik")),
        "parametre_detay": kalem.get("parametre_detay") or "",
        "baski_oneri": kalem.get("baski_oneri") or "",
        "dosyalar": [],   # [{"ad":..., "boyut":..., "uretildi":bool}]
        "eksik": [],      # ["<aciklama>", ...]
    }
    urun_id = sonuc["id"]

    if sonuc["parametrik"]:
        yol = kalem.get("stl_ucu") or (
            "/api/shop/yonet/stl?siparis_no=%s&kalem=%d" % (_q(siparis_no), i))
        hedef_ad = "%02d_%s.stl" % (i + 1, guvenli_ad(urun_id))
        r = dosya_indir(taban, yol, anahtar, os.path.join(klasor, hedef_ad))
        if r["durum"] == "ok":
            sonuc["dosyalar"].append({"ad": hedef_ad, "boyut": r["boyut"], "uretildi": True})
        else:
            sonuc["eksik"].append(r.get("not") or ("derleme/indirme hatasi (kod %s)" % r.get("kod")))
        return sonuc

    # Normal urun: once parca listesi, sonra parca basina indir.
    liste_yol = kalem.get("stl_liste_ucu") or ("/api/shop/yonet/stl-liste?id=%s" % _q(urun_id))
    kod, obj = api_json(taban, liste_yol, anahtar)
    parcalar = (obj or {}).get("parcalar") if isinstance(obj, dict) else None
    parcalar = parcalar or []
    if not parcalar:
        not_m = (obj or {}).get("not") if isinstance(obj, dict) else None
        sonuc["eksik"].append(not_m or ("parca listesi alinamadi (kod %s)" % kod))
        return sonuc
    for p in parcalar:
        dosya = p.get("dosya")
        if not dosya:
            continue
        yol = "/api/shop/yonet/stl?id=%s&dosya=%s&siparis_no=%s" % (
            _q(urun_id), _q(dosya), _q(siparis_no))
        hedef_ad = "%02d_%s" % (i + 1, guvenli_ad(dosya))
        r = dosya_indir(taban, yol, anahtar, os.path.join(klasor, hedef_ad))
        if r["durum"] == "ok":
            sonuc["dosyalar"].append({"ad": hedef_ad, "boyut": r["boyut"]})
        else:
            sonuc["eksik"].append("%s: %s" % (dosya, r.get("not") or ("kod %s" % r.get("kod"))))
    return sonuc


# ----------------------------------------------------------------- fis

def _boyut(b):
    b = b or 0
    if b >= 1048576:
        return "%.1f MB" % (b / 1048576.0)
    if b >= 1024:
        return "%d KB" % round(b / 1024.0)
    return "%d B" % b


def fis_metni(siparis, sonuclar, klasor):
    """Buyuk/net baski fisini string olarak uretir (anahtar YOK)."""
    mus = siparis.get("musteri") or {}
    cizgi = "=" * 64
    L = [cizgi,
         "  BASKI FISI — Siparis %s" % siparis.get("siparis_no", "?"),
         "  Musteri: %s  ·  %s" % (mus.get("ad") or "-", mus.get("tel") or "-"),
         "  Adres  : %s" % (mus.get("adres") or "-"),
         cizgi, ""]
    toplam_dosya = 0
    for s in sonuclar:
        etiket = "  [OLCUYE OZEL / SARI]" if s["parametrik"] else ""
        L.append("  [%d] %s   × %s%s" % (s["kalem"] + 1, s["baslik"], s["adet"], etiket))
        # MALZEME + RENK — uretimin en pahali hatasi; goze batsin (kaynak yazim korunur).
        L.append("      >>> MALZEME: %s      RENK: %s <<<"
                 % (s["malzeme"], s["renk"]))
        if s.get("parametre_detay"):
            L.append("      Olcu   : %s" % s["parametre_detay"])
        if s.get("baski_oneri"):
            L.append("      Baski  : %s" % s["baski_oneri"])
        if s["dosyalar"]:
            L.append("      Dosyalar:")
            for d in s["dosyalar"]:
                ek = " (uretildi)" if d.get("uretildi") else ""
                L.append("        - %s  (%s)%s" % (d["ad"], _boyut(d.get("boyut")), ek))
                toplam_dosya += 1
        # Eksik/dosyasiz kalem: SESSIZ ATLAMA YOK.
        if s["eksik"]:
            L.append("      !! dosya yok: %s — yonetim sayfasindaki nota bak" % s["id"])
            for m in s["eksik"]:
                if m:
                    L.append("         (%s)" % m)
        L.append("")
    L.append(cizgi)
    L.append("  Toplam %d kalem · %d dosya indirildi" % (len(sonuclar), toplam_dosya))
    L.append("  Klasor: %s" % klasor)
    L.append(cizgi)
    return "\n".join(L)


# ----------------------------------------------------------------- bambu

def bambu_uygulama_yolu():
    """Kurulu Bambu Studio .app yolu ya da None."""
    for p in BAMBU_ADAYLARI:
        if os.path.isdir(p):
            return p
    return None


def bambu_ac(dosyalar, klasor):
    """Dosyalari Bambu Studio'da acar (macOS). Kurulu degilse cokmez, mesaj basar."""
    app = bambu_uygulama_yolu()
    if not app:
        print("Bambu Studio bulunamadi — dosyalar surada: %s" % klasor)
        return False
    try:
        subprocess.run(["open", "-a", app] + list(dosyalar), check=False)
        print("Bambu Studio'da aciliyor: %d dosya (%s)" % (len(dosyalar), app))
        return True
    except Exception as e:
        print("Bambu Studio acilamadi (%s) — dosyalar surada: %s" % (e, klasor))
        return False


# ----------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("siparis_no", help="siparis numarasi (or. PR250717-1234)")
    ap.add_argument("--sadece-indir", action="store_true",
                    help="Bambu Studio'da ACMA, sadece indir + fis bas")
    ap.add_argument("--klasor", default=None,
                    help="hedef klasor (varsayilan ~/Pruvo-Baskilar/<siparis_no>/)")
    ap.add_argument("--anahtar", default=None, help="yonetim anahtari (yoksa dosyadan)")
    ap.add_argument("--taban", default=os.environ.get("PRUVO_TABAN", VARSAYILAN_TABAN),
                    help="API taban URL'si (varsayilan %s)" % VARSAYILAN_TABAN)
    args = ap.parse_args(argv)

    anahtar = anahtar_oku(args.anahtar)
    if not anahtar:
        print("HATA: yonetim anahtari bulunamadi (.yonet-anahtar / --anahtar / "
              "YONET_ANAHTAR).", file=sys.stderr)
        return 2

    siparis, hata = siparis_bul(args.taban, anahtar, args.siparis_no)
    if not siparis:
        print("HATA: %s" % hata, file=sys.stderr)
        return 4

    klasor = args.klasor or os.path.join(
        os.path.expanduser("~"), "Pruvo-Baskilar", args.siparis_no)
    try:
        os.makedirs(klasor, exist_ok=True)
    except OSError as e:
        print("HATA: klasor olusturulamadi: %s (%s)" % (klasor, e), file=sys.stderr)
        return 5

    kalemler = siparis.get("kalemler") or []
    sonuclar = [kalem_isle(args.taban, anahtar, args.siparis_no, k, klasor) for k in kalemler]

    print(fis_metni(siparis, sonuclar, klasor))

    tum_dosyalar = [os.path.join(klasor, d["ad"]) for s in sonuclar for d in s["dosyalar"]]
    if args.sadece_indir:
        return 0
    if not tum_dosyalar:
        print("Indirilen dosya yok — Bambu Studio acilmadi. Klasor: %s" % klasor)
        return 0
    bambu_ac(tum_dosyalar, klasor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
