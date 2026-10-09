#!/usr/bin/env python3
"""KOPRU GRUP KOSUCUSU (kopru-15, 8 Eki 2026) — grup adimlarini tek DETERMINISTIK koşucuya baglar.

    python3 tools/kopru-grup-kos.py --tur rolyef --tur braille
    python3 tools/kopru-grup-kos.py --grup G3            (grup -> tur listesi YALNIZ `GRUPLAR`da)
    python3 tools/kopru-grup-kos.py --grup G5 --kuru     (agsiz: kosacak komutlari basar)

Her tur icin SIRAYLA (paralel YOK, Blender YOK):
  1. render : manifest `uretec` -> foto-uretec-kosucu.py `URETEC_CLI` satiri (betik/bayraklar/on_adim TURETILIR,
              ikinci kopya YOK) + TeKiN kaydinin `ornek.girdi`si (ayni `uretec`li ilk kayit; bust -> rolyef) ->
              [on_adim (AG)] -> uretec -> onizleme.png -> cwebp -q 90. Gecici dizin tempfile'da, tur bitince SILINIR.
  2. R2     : wrangler r2 object put pruvo-media/foto/ornek/<kod>-1-render.webp --remote (CLOUDFLARE_ACCOUNT_ID
              foto-onizleme.py `HESAP`tan; SIR DOSYASI OKUNMAZ) -> https://media.pruvo3d.com/... HTTP 200 DOGRULANIR.
  3. D1     : `pruvo-katalog-onizleme` (-c shop/wrangler.onizleme.toml) foto_acik INSERT OR REPLACE. Ad SABIT;
              komutta `pruvo-katalog` (CANLI) gecen her cagri REDDEDILIR (fail-closed), toml adi tutmazsa DUR.
  4. olcum  : tools/foto-ornek-uc-uca.py --tur <kod> -> ciktisi AYNEN basilir.
  5. satir  : `KOSU tur=<kod> RENDER=ok|<hata> R2=200|<kod> D1=ok|<hata> HAZIR=evet|hayir eksik=<①..⑥>`;
              son satir `KOPRU_GRUP turler=<n> hazir=<h>/<n> rc=<0|1>` (rc 0 = her adim ok VE her tur HAZIR).
              Bir turun hatasi digerlerini DURDURMAZ.
Yer tutucu ornek degerleri (`"<PNG YOLU>, gri gradyan"`, `"<100 elemanli dizi, sinus>"`) gecici dizinde
deterministik uretilir (gri gradyan PNG / genlik dizisi = foto-ornek-uc-uca.ORNEK_GENLIK, 0..1; ikinci formul YOK —
kopru-15 SON3: [-1,1] sinus uretec/VERI `ses` tipinin 0..1 sinirinda `RET: genlik[17] < min 0.0` aliyordu).
TEST KANCASI: KOPRU_GRUP_SAHTE=<betik> -> her dis komut `python3 <betik> <komut...>` ile kosar (izole test).
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSUCU = os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
ONIZLEME_ARAC = os.path.join(KOK, "tools", "foto-onizleme.py")
OLCUM = os.path.join(KOK, "tools", "foto-ornek-uc-uca.py")
ONIZLEME_TOML_GORELI = "shop/wrangler.onizleme.toml"
D1_ONIZLEME = "pruvo-katalog-onizleme"
D1_CANLI = "pruvo-katalog"
R2_ONEK = "pruvo-media/foto/ornek/"
MEDYA_URL = "https://media.pruvo3d.com/foto/ornek/"
CWEBP = "/opt/homebrew/bin/cwebp"
KAYIT = os.environ.get("KOPRU_KAYIT") or os.path.expanduser(
    "~/dev/pruvo-jenerator/jeneratorler/kopru/kopru_kayitlari.json")
GRUPLAR = {
    "G3": ["rolyef", "braille", "ses", "bust"],
    "G5": ["topo", "sehir", "yildiz", "koordinat"],
}
URETEC_SURE_SN = 600


class Red(Exception):
    pass


def _kosucu():
    s = importlib.util.spec_from_file_location("foto_uretec_kosucu", KOSUCU)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def hesap_kimligi():
    with open(ONIZLEME_ARAC, encoding="utf-8") as f:
        m = re.search(r'(?m)^HESAP\s*=\s*"([0-9a-f]{32})"', f.read())
    if not m:
        raise SystemExit("HATA hesap kimligi foto-onizleme.py'de yok: DUR")
    return m.group(1)


def toml_d1_denetle():
    with open(os.path.join(KOK, ONIZLEME_TOML_GORELI), encoding="utf-8") as f:
        m = re.search(r'(?m)^database_name\s*=\s*"([a-z0-9-]+)"', f.read())
    if not m or m.group(1) != D1_ONIZLEME:
        raise SystemExit("HATA onizleme toml D1 adi %r != %s: DUR" % (m and m.group(1), D1_ONIZLEME))


def wrangler():
    return ["npx", "--no-install", "--prefix", "shop", "wrangler"]


def d1_komutu(sql):
    k = wrangler() + ["d1", "execute", D1_ONIZLEME, "--remote", "-c", ONIZLEME_TOML_GORELI, "--command", sql]
    if D1_CANLI in k[:-1] or D1_ONIZLEME not in k or ONIZLEME_TOML_GORELI not in k:
        raise Red("canli-d1-reddedildi")
    return k


def r2_komutu(kod, dosya):
    return wrangler() + ["r2", "object", "put", R2_ONEK + "%s-1-render.webp" % kod, "--file", dosya,
                         "--content-type", "image/webp", "--remote"]


def kos(komut, env=None, cwd=KOK, zaman=URETEC_SURE_SN):
    sahte = os.environ.get("KOPRU_GRUP_SAHTE")
    if sahte:
        komut = [sys.executable, sahte] + list(komut)
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=zaman, cwd=cwd,
                           env=dict(os.environ, **(env or {})))
    except subprocess.TimeoutExpired:
        return 124, "", "sure-asimi"
    except OSError as e:
        return 127, "", "baslatilamadi: %s" % e
    return p.returncode, p.stdout, p.stderr


def _ozet(metin):
    s = (metin or "").strip().splitlines()
    return re.sub(r"\s+", "_", s[-1])[:120] if s else "bos"


# ------------------------------------------------------------------ plan (tur -> uretec + ornek)
def plan_kur(kodlar):
    k = _kosucu()
    manifest, cli = k.manifest_oku(), k.cli_tablosu()
    with open(KAYIT, encoding="utf-8") as f:
        kayitlar = json.load(f)["kayitlar"]
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    planlar = []
    for kod in kodlar:
        t = manifest.get(kod)
        if not t:
            planlar.append({"kod": kod, "hata": "manifest-tur-yok"})
            continue
        g = cli.get(t.get("uretec"))
        kayit = next((r for r in kayitlar if r.get("uretec") == t.get("uretec")), None)
        if not g or not kayit or not isinstance(kayit.get("ornek"), dict):
            planlar.append({"kod": kod, "hata": "uretec-ya-da-kayit-yok"})
            continue
        planlar.append({"kod": kod, "g": g, "kayit": kayit, "jen": jen, "py": py})
    return planlar


def _png_gri_gradyan(yol, w=256, h=192):
    satirlar = b"".join(b"\x00" + bytes(((x * 255) // (w - 1) + (y * 64) // (h - 1)) % 256 for x in range(w))
                        for y in range(h))
    def parca(tip, veri):
        return struct.pack(">I", len(veri)) + tip + veri + struct.pack(">I", zlib.crc32(tip + veri) & 0xffffffff)
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                + parca(b"IDAT", zlib.compress(satirlar, 9)) + parca(b"IEND", b""))


def ornek_genlik():
    """Ses genlik ornegi TEK kaynaktan: tools/foto-ornek-uc-uca.py `ORNEK_GENLIK` (0..1)."""
    s = importlib.util.spec_from_file_location("foto_ornek_uc_uca", OLCUM)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return list(m.ORNEK_GENLIK)


def ornek_girdisi(kayit, dizin):
    """`ornek.girdi` -> uretec JSON; yer tutucu (`<...>`) degerler deterministik uretilir."""
    tipler = {p.get("ad"): p.get("tip") for p in kayit.get("parametreler") or []}
    u = {}
    for ad, v in (kayit["ornek"].get("girdi") or {}).items():
        if isinstance(v, str) and v.startswith("<"):
            if tipler.get(ad) == "dosya":
                v = os.path.join(dizin, "ornek-%s.png" % ad)
                _png_gri_gradyan(v)
            elif "dizi" in v:
                n = int((re.search(r"<(\d+)", v) or re.search(r"(\d+)", "100")).group(1))
                v = ornek_genlik()
                if len(v) != n:
                    raise Red("yer-tutucu-boyu:%s=%d ORNEK_GENLIK=%d" % (ad, n, len(v)))
            else:
                raise Red("yer-tutucu-cozulemedi:%s" % ad)
        u[ad] = v
    # Kopru `cagri.sabit` (anahtarlik: {anahtarlik: true}) uretece HER cagride gider — kosucu esle_anahtarlik ile
    # ayni sozlesme. Yoksa isimlik_uret kulak alanlarini RET eder (9 Eki, anahtarlik-kart olcumu).
    u.update((kayit.get("cagri") or {}).get("sabit") or {})
    return u


def render_komutlari(p, dizin):
    g, kayit = p["g"], p["kayit"]
    ugirdi, cikti = os.path.join(dizin, "girdi.json"), os.path.join(dizin, "cikti")
    komutlar = []
    uretec = [p["py"], os.path.join(p["jen"], g["betik"])] + list(g.get("bayraklar", []))
    if g.get("on_adim"):
        oa, veri = g["on_adim"], os.path.join(dizin, "veri.json")
        komutlar.append(("on_adim", [p["py"], os.path.join(p["jen"], oa["betik"])] + list(oa.get("bayraklar", []))
                         + [oa["girdi_bayragi"], ugirdi, oa["cikti_bayragi"], veri]))
        uretec += [g["veri_bayragi"], veri]
    komutlar.append(("uretec", uretec + ["--girdi", ugirdi, "--cikti", cikti]))
    png = os.path.join(cikti, (kayit.get("cikti") or {}).get("onizleme_png", "onizleme.png"))
    webp = os.path.join(dizin, "%s-1-render.webp" % p["kod"])
    komutlar.append(("webp", [CWEBP, "-q", "90", png, "-o", webp]))
    return komutlar, webp


def d1_sql(kod):
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return "INSERT OR REPLACE INTO foto_acik (tur, acik, guncel) VALUES ('%s',1,'%s')" % (kod, iso)


# ------------------------------------------------------------------ adimlar
def adim_render(p, dizin):
    with open(os.path.join(dizin, "girdi.json"), "w", encoding="utf-8") as f:
        json.dump(ornek_girdisi(p["kayit"], dizin), f, ensure_ascii=False, sort_keys=True)
    komutlar, webp = render_komutlari(p, dizin)
    for ad, komut in komutlar:
        rc, _, err = kos(komut, cwd=p["jen"] if os.path.isdir(p["jen"]) else KOK)
        if rc != 0:
            return "%s-rc%d:%s" % (ad, rc, _ozet(err)), None
    if not os.path.isfile(webp) or os.path.getsize(webp) == 0:
        return "webp-yok", None
    return "ok", webp


def http_durum(url):
    rc, out, _ = kos(["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", url], zaman=60)
    kod = (out or "").strip()[-3:]
    return kod if rc == 0 and kod.isdigit() else "curl-rc%d" % rc


def adim_r2(p, webp, hesap):
    rc, _, err = kos(r2_komutu(p["kod"], webp), env={"CLOUDFLARE_ACCOUNT_ID": hesap}, zaman=180)
    if rc != 0:
        return "put-rc%d:%s" % (rc, _ozet(err))
    durum = http_durum(MEDYA_URL + "%s-1-render.webp?v=%d" % (p["kod"], int(time.time())))
    return "200" if durum == "200" else durum


def adim_d1(p, hesap):
    try:
        komut = d1_komutu(d1_sql(p["kod"]))
    except Red as e:
        return str(e)
    rc, _, err = kos(komut, env={"CLOUDFLARE_ACCOUNT_ID": hesap}, zaman=180)
    return "ok" if rc == 0 else "rc%d:%s" % (rc, _ozet(err))


def adim_olcum(kod):
    rc, out, err = kos([sys.executable, OLCUM, "--tur", kod], zaman=900)
    metin = (out or "") + (err or "")
    sys.stdout.write(metin if metin.endswith("\n") or not metin else metin + "\n")
    hazir = re.search(r"(?m)^HAZIR=(\d+)/(\d+)", out or "")
    evet = bool(hazir) and hazir.group(1) == hazir.group(2) != "0"
    eksik = "".join(sorted(set(re.findall(r"(?m)^\s+([①②③④⑤⑥])\s+EKSIK", out or ""))))
    return evet, eksik or ("-" if evet else "olculemedi")


def tur_kos(p, hesap):
    kod = p["kod"]
    sonuc = {"RENDER": "-", "R2": "-", "D1": "-"}
    if p.get("hata"):
        sonuc["RENDER"] = p["hata"]
    else:
        dizin = tempfile.mkdtemp(prefix="kopru-grup-%s-" % kod)
        try:
            sonuc["RENDER"], webp = adim_render(p, dizin)
            if webp:
                sonuc["R2"] = adim_r2(p, webp, hesap)
            if sonuc["R2"] == "200":
                sonuc["D1"] = adim_d1(p, hesap)
        except Red as e:
            sonuc["RENDER"] = str(e)
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
    evet, eksik = adim_olcum(kod)
    adim_ok = sonuc["RENDER"] == "ok" and sonuc["R2"] == "200" and sonuc["D1"] == "ok"
    print("KOSU tur=%s RENDER=%s R2=%s D1=%s HAZIR=%s eksik=%s" % (
        kod, sonuc["RENDER"], sonuc["R2"], sonuc["D1"], "evet" if evet else "hayir", eksik))
    sys.stdout.flush()
    return adim_ok, evet


def kuru(planlar, hesap):
    for p in planlar:
        if p.get("hata"):
            print("KURU tur=%s HATA=%s" % (p["kod"], p["hata"]))
            continue
        d = "<gecici>"
        komutlar, webp = render_komutlari(p, d)
        print("KURU tur=%s ADIM=render KOMUT=%s" % (p["kod"], " && ".join(" ".join(k) for _, k in komutlar)))
        print("KURU tur=%s ADIM=r2 KOMUT=CLOUDFLARE_ACCOUNT_ID=%s %s && curl -sI %s%s-1-render.webp" % (
            p["kod"], hesap, " ".join(r2_komutu(p["kod"], webp)), MEDYA_URL, p["kod"]))
        try:
            d1 = " ".join(d1_komutu(d1_sql(p["kod"])))
        except Red as e:
            d1 = "RED:%s" % e
        print("KURU tur=%s ADIM=d1 KOMUT=%s" % (p["kod"], d1))
        print("KURU tur=%s ADIM=olcum KOMUT=python3 tools/foto-ornek-uc-uca.py --tur %s" % (p["kod"], p["kod"]))


def main():
    ap = argparse.ArgumentParser(description="kopru-15 grup kosucusu (render -> R2 -> onizleme D1 -> olcum)")
    ap.add_argument("--tur", action="append", default=[])
    ap.add_argument("--grup", choices=sorted(GRUPLAR))
    ap.add_argument("--kuru", action="store_true", help="agsiz: kosacak komutlari basar")
    a = ap.parse_args()
    kodlar = list(a.tur) + (GRUPLAR[a.grup] if a.grup else [])
    if not kodlar:
        print("KOPRU_GRUP turler=0 hazir=0/0 rc=2")
        return 2
    toml_d1_denetle()
    hesap = hesap_kimligi()
    planlar = plan_kur(kodlar)
    if a.kuru:
        kuru(planlar, hesap)
        print("KOPRU_GRUP turler=%d hazir=0/%d rc=0 (kuru)" % (len(planlar), len(planlar)))
        return 0
    tamam, hazir = 0, 0
    for p in planlar:
        ok, evet = tur_kos(p, hesap)
        tamam += ok
        hazir += evet
    n = len(planlar)
    rc = 0 if tamam == n and hazir == n else 1
    print("KOPRU_GRUP turler=%d hazir=%d/%d rc=%d" % (n, hazir, n, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
