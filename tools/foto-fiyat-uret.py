#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FOTO FIYAT URETECI — `foto_fiyat` satirlarini MANIFESTTEN uretir (elle satir YAZILMAZ).

Tek kaynak: foto-uretim-veri.js `turler[]` (sozlesme §6). Her tur icin
  olcu_mm.en_az .. olcu_mm.en_cok, adim fiyat.adim_mm  ->  fiyat_kurus = mm x 1000
(`fiyat.formul == "mm_x_10tl"`; baska formul TANINMAZ -> rc 1, satir uretilmez).

KIPLER
  (varsayilan) KURU : SQL'i basar + canli tabloyla farki sayar (eklenecek / silinecek /
                      degisecek). Canli okuma SALT OKUMA: `wrangler d1 execute --remote --json`
                      ile tek SELECT. Hicbir yere YAZMAZ.
  --canli-json <f>  : canli tablo yerine fikstur (wrangler `--json` ciktisi ya da duz satir
                      listesi). Testin kolu; ag/kimlik ISTEMEZ.
  --uygula          : uretilen SQL'i canli D1'e yazar. YALNIZ MIMAR kosar (para sinifi).

SILINECEK: manifestteki bir turun canli satiri plan disindaysa (aralik/adim disi) DELETE.
Manifestte OLMAYAN turun canli satiri YABANCI sayilir: raporlanir, SILINMEZ.

CIKTI (son satirlar, makine okur):
  TUR=<kod> PLAN=<n> CANLI=<n> EKLENECEK=<n> SILINECEK=<n> DEGISECEK=<n>
  YABANCI=<n> ARALIK_DISI=<n> FARK_TOPLAM=<n> KIP=KURU|UYGULA CANLI_KAYNAK=<d1|fikstur>
CIKIS KODU: 0 tamam · 1 manifest/plan gecersiz (aralik disi satir dahil) · 3 OLCULEMEDI
(canli okunamadi; KURU'da SQL yine basilir, fark sayilmaz).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

KOK_VARSAYILAN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_AD = "pruvo-katalog"
CANLI_SQL = "SELECT tur, olcu_mm, fiyat_kurus FROM foto_fiyat ORDER BY tur, olcu_mm"

# Manifesti tarayici dosyasindan okur (vm baglaminda; global kirlenmez).
NODE_OKU = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "process.stdout.write(JSON.stringify(k.PRUVO_FOTO.turler));"
)


def manifest_oku(kok):
    yol = os.path.join(kok, "foto-uretim-veri.js")
    p = subprocess.run(["node", "-e", NODE_OKU, yol], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("MANIFEST OKUNAMADI: " + (p.stderr or "")[-500:])
    return json.loads(p.stdout)


def fiyat_kurus(mm):
    """Formul mm_x_10tl: 1 mm = 10,00 TL = 1000 kurus."""
    return mm * 1000


def plan_uret(turler):
    """Doner: (satirlar[{tur,olcu_mm,fiyat_kurus}], hatalar[str])."""
    satirlar, hatalar = [], []
    for t in turler:
        kod = t.get("kod")
        f = t.get("fiyat") or {}
        a = t.get("olcu_mm") or {}
        en_az, en_cok, adim = a.get("en_az"), a.get("en_cok"), f.get("adim_mm")
        if f.get("formul") != "mm_x_10tl":
            hatalar.append("%s:formul" % kod)
            continue
        if not all(isinstance(x, int) and x > 0 for x in (en_az, en_cok, adim)) or en_cok < en_az:
            hatalar.append("%s:aralik" % kod)
            continue
        mm = en_az
        while mm <= en_cok:
            satirlar.append({"tur": kod, "olcu_mm": mm, "fiyat_kurus": fiyat_kurus(mm)})
            mm += adim
    return satirlar, hatalar


def aralik_disi(satirlar, turler):
    """Plan satiri turun olcu_mm araliginin disinda mi (bagimsiz yeniden olcum)."""
    ar = {t["kod"]: t.get("olcu_mm") or {} for t in turler}
    n = 0
    for s in satirlar:
        a = ar.get(s["tur"]) or {}
        if not (a.get("en_az", 1) <= s["olcu_mm"] <= a.get("en_cok", 0)):
            n += 1
    return n


def canli_ayristir(ham):
    """wrangler --json ciktisi ([{results:[..],success}]) ya da duz liste -> satir listesi."""
    i = ham.find("[")
    if i < 0:
        raise ValueError("json-yok")
    v = json.loads(ham[i:])
    if v and isinstance(v[0], dict) and "results" in v[0]:
        if not v[0].get("success", False):
            raise ValueError("basarisiz")
        v = v[0].get("results") or []
    return [{"tur": str(r["tur"]), "olcu_mm": int(r["olcu_mm"]), "fiyat_kurus": int(r["fiyat_kurus"])} for r in v]


def wrangler(kok, argumanlar):
    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB_AD, "--remote", "--json"] + argumanlar
    return subprocess.run(komut, cwd=os.path.join(kok, "shop"), capture_output=True, text=True)


def canli_oku(kok, fikstur):
    if fikstur:
        with open(fikstur, encoding="utf-8") as f:
            return canli_ayristir(f.read()), "fikstur"
    p = wrangler(kok, ["--command", CANLI_SQL])
    if p.returncode != 0:
        raise ValueError("wrangler rc=%d %s" % (p.returncode, (p.stderr or "")[-300:]))
    return canli_ayristir(p.stdout or ""), "d1"


def fark(plan, canli, turler):
    kodlar = [t["kod"] for t in turler]
    p = {(s["tur"], s["olcu_mm"]): s["fiyat_kurus"] for s in plan}
    c = {(s["tur"], s["olcu_mm"]): s["fiyat_kurus"] for s in canli}
    sonuc = {}
    for kod in kodlar:
        pk = {k for k in p if k[0] == kod}
        ck = {k for k in c if k[0] == kod}
        sonuc[kod] = {
            "plan": len(pk), "canli": len(ck),
            "eklenecek": sorted(pk - ck), "silinecek": sorted(ck - pk),
            "degisecek": sorted(k for k in pk & ck if p[k] != c[k]),
        }
    yabanci = sorted(k for k in c if k[0] not in kodlar)
    return sonuc, yabanci


def sql_uret(plan, sonuc):
    guncel = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    p = {(s["tur"], s["olcu_mm"]): s["fiyat_kurus"] for s in plan}
    satir = []
    for kod, s in sonuc.items():
        for k in s["eklenecek"] + s["degisecek"]:
            satir.append(
                "INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('%s', %d, %d, '%s')"
                " ON CONFLICT(tur, olcu_mm) DO UPDATE SET fiyat_kurus = excluded.fiyat_kurus,"
                " guncel = excluded.guncel;" % (k[0], k[1], p[k], guncel))
        for k in s["silinecek"]:
            satir.append("DELETE FROM foto_fiyat WHERE tur = '%s' AND olcu_mm = %d;" % (k[0], k[1]))
    return satir


def main():
    ap = argparse.ArgumentParser(description="foto_fiyat satirlarini manifestten uret (varsayilan KURU)")
    ap.add_argument("--canli-json", help="canli tablo yerine fikstur dosyasi")
    ap.add_argument("--uygula", action="store_true", help="SQL'i canli D1'e yaz (YALNIZ MIMAR)")
    ap.add_argument("--kok", default=KOK_VARSAYILAN, help="repo koku (manifest + shop/)")
    a = ap.parse_args()

    turler = manifest_oku(a.kok)
    plan, hatalar = plan_uret(turler)
    ad = aralik_disi(plan, turler)
    if hatalar or ad:
        print("PLAN GECERSIZ: hatalar=%s aralik_disi=%d" % (",".join(hatalar), ad))
        print("ARALIK_DISI=%d" % ad)
        return 1
    if any(s["fiyat_kurus"] <= 0 or s["fiyat_kurus"] > 10000000 for s in plan):
        print("PLAN GECERSIZ: fiyat_kurus 1..10000000 disinda")
        return 1
    try:
        canli, kaynak = canli_oku(a.kok, a.canli_json)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("-- KURU: plan (canli okunamadi, fark sayilmadi)")
        for s in plan:
            print("-- %s %d mm %d kurus" % (s["tur"], s["olcu_mm"], s["fiyat_kurus"]))
        print("HAL=OLCULEMEDI sebep=%s (hesap secimi icin CLOUDFLARE_ACCOUNT_ID ortam degiskeni)" % str(e)[:200])
        return 3
    sonuc, yabanci = fark(plan, canli, turler)
    sql = sql_uret(plan, sonuc)
    print("-- foto_fiyat SQL (%s, %d satir)" % ("UYGULA" if a.uygula else "KURU", len(sql)))
    for s in sql:
        print(s)
    toplam = 0
    for kod, s in sonuc.items():
        n = len(s["eklenecek"]) + len(s["silinecek"]) + len(s["degisecek"])
        toplam += n
        print("TUR=%s PLAN=%d CANLI=%d EKLENECEK=%d SILINECEK=%d DEGISECEK=%d" % (
            kod, s["plan"], s["canli"], len(s["eklenecek"]), len(s["silinecek"]), len(s["degisecek"])))
    print("YABANCI=%d ARALIK_DISI=%d FARK_TOPLAM=%d KIP=%s CANLI_KAYNAK=%s" % (
        len(yabanci), ad, toplam, "UYGULA" if a.uygula else "KURU", kaynak))
    if not a.uygula or not sql:
        return 0
    fd, yol = tempfile.mkstemp(suffix=".sql", prefix="foto-fiyat-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(sql) + "\n")
        p = wrangler(a.kok, ["--file", yol])
        print("UYGULA_RC=%d" % p.returncode)
        return 0 if p.returncode == 0 else 1
    finally:
        os.unlink(yol)


if __name__ == "__main__":
    sys.exit(main())
