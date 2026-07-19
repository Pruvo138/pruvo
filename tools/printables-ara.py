#!/usr/bin/env python3
"""Printables'te MARKA/terim arar, sitede OLMAYAN + satilabilir + gurultusuz model ID'lerini verir.
Thingiverse'teki thing-ara.py'nin esdegeri.

Kullanim:  python3 tools/printables-ara.py "Renault" [max]
   -> aday model ID'lerini bir satirda (bosluk ayirli) yazar + id/lisans/baslik listesi basar.

ELER:  * CC-...-NC (satilamaz) lisanslar        (satilabilir() kurali)
       * anahtarlik/logo/amblem/minyatur gurultusu (COP listesi)
       * `.urun-kaynaklari.json`'da zaten kayitli printables model ID'leri

Token GEREKMEZ (Printables public GraphQL). Sir icermez.
"""
import importlib.util, os, re, sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

# Printables resmi arayuzundeki lisans ID'leri (2026-07-19). Her biri ayri sorgulanir.
# Deger: (UI/API kimligi, beklenen API kisaltmasi). NC/OCL/Standard bilerek yoktur.
SATILABILIR_LISANSLAR = (
    ("7", "CC0"), ("1", "CC-BY"), ("2", "CC-BY-SA"), ("8", "CC-BY-ND"),
    ("9", "GPL 2.0"), ("12", "GPL 3.0"), ("10", "LGPL"), ("11", "BSD"),
)

# printables-api.py'yi BU dosyanin yaninda (worktree/main hangisiyse) yukle — ROOT'a bagli degil
# (worktree kopyasi kendi cekirdegini goreblsin; marka_kelime_gecer testi de bunu kullanir).
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(_HERE, "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def mevcut_idler():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'printables\.com/model/(\d+)', blob):
            ids.add(m)
        for m in re.findall(r'printables[:/](\d{3,})', blob):
            ids.add(m)
    return ids


def main(term, maxn, tam_kelime=False, derin=False, cikis_limiti=None):
    """term/marka ara, sitede OLMAYAN uygun aday model ID'lerini bas.

    Sayfalama (pagination) ile keeper-cap AYRI (2026-07-18 duzeltme; thing-ara.py deseni):
      - derin=False (varsayilan, GERIYE-UYUMLU): dongu `maxn` keeper toplayinca DURUR
        (eski davranis birebir). Hizli; parity-backfill/CLI eski cagrilari icin.
      - derin=True (--derin): `maxn` dongoyu DURDURMAZ; ham havuz IKINCIL tavana (offset<3000)
        ya da `total` tukenene kadar TAM taranir, deterministik filtreleri gecen TUM adaylar
        toplanir. Boylece uygun havuz erken kesilmez (Toyota ~40 -> yuzler).
    `cikis_limiti` (opsiyonel): siralamadan sonra cikti listesini kirpar (None=kirpma yok)."""
    mevcut = mevcut_idler()
    bulunan, elenen_cop, elenen_nc, elenen_kelime = [], [], [], []
    seen = set()
    offset = 0
    total = None
    toplam_eslesme = 0
    lisans_indeksi = 0
    lisans_bulunan = 0
    while lisans_indeksi < len(SATILABILIR_LISANSLAR):
        if offset >= 3000:
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        lisans_id = SATILABILIR_LISANSLAR[lisans_indeksi][0]
        try:
            res = pr.search(term, limit=30, offset=offset, ordering="popular", licenses=[lisans_id])
        except Exception as e:
            print("ARAMA HATA (lisans %s, offset %d):" % (lisans_id, offset), e)
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        total = res["totalCount"] if total is None else total
        items = res["items"]
        if not items:
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        for h in items:
            pid = str(h["id"])
            if pid in seen:
                continue
            seen.add(pid)
            if pid in mevcut:
                continue
            name = (h.get("name") or "").replace("\n", " ")
            abbr = ((h.get("license") or {}).get("abbreviation")) or ""
            dl = h.get("downloadCount") or 0
            likes = h.get("likesCount") or 0
            # --tam-kelime: baslikta marka TAM KELIME degilse (Oxford/afford/Food) ELE
            if tam_kelime and not pr.marka_kelime_gecer(name, term):
                elenen_kelime.append((pid, name)); continue
            if not pr.satilabilir(abbr):
                elenen_nc.append((pid, abbr, name)); continue    # NC = yasal, POPULERLIK DELMEZ
            pop = pr.populer(dl, likes)
            if pr.is_nobypass(name):
                elenen_cop.append((pid, name)); continue         # logo/amblem VEYA marka-merch -> populerlik DELMEZ, hep ele
            if pr.is_cop(name) and not pop:
                elenen_cop.append((pid, name)); continue         # cop VE populer degil -> ele
            bulunan.append((pid, abbr, name, dl, likes, pr.is_cop(name)))  # son alan: populer-cop mu
            lisans_bulunan += 1
            # keeper-cap SADECE derin-olmayan (eski) modda dongoyu keser
            if not derin and lisans_bulunan >= maxn:
                break
        offset += 30
        if offset >= (total or 0) or (not derin and lisans_bulunan >= maxn):
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0

    # EN YUKSEK ONCELIK: talep (begeni + indirme) cok olan urun basa. Populer-cop olanlar da burada.
    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, dl) azalan
    havuz_toplam = len(bulunan)   # kirpmadan ONCE toplanan gercek aday sayisi (kabul olcumu)
    if not derin:
        bulunan = bulunan[:maxn]
    elif cikis_limiti is not None:
        bulunan = bulunan[:cikis_limiti]

    if elenen_kelime:
        print("--- MARKA ALT-DIZE elenen %d ('%s' tam kelime degil: Oxford/afford/Food gibi) ---"
              % (len(elenen_kelime), term))
        for pid, name in elenen_kelime[:15]:
            print("  x %s  %s" % (pid, name[:60]))
    if elenen_nc:
        print("--- SATILAMAZ (NC) elenen %d (populerlik DELMEZ — yasal) ---" % len(elenen_nc))
        for pid, abbr, name in elenen_nc[:15]:
            print("  x %s  %-12s %s" % (pid, abbr, name[:55]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur; populer OLMAYAN) ---" % len(elenen_cop))
        for pid, name in elenen_cop[:15]:
            print("  x %s  %s" % (pid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[5])
    kirpma = "" if cikis_limiti is None else " (cikis %d'e kirpildi; havuz %d)" % (len(bulunan), havuz_toplam)
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, NC %d, cop %d elendi; "
          "populer-cop ISTISNA %d)%s ==="
          % (term, len(bulunan), toplam_eslesme, len(mevcut & seen), len(elenen_nc), len(elenen_cop), pop_cop, kirpma))
    for pid, abbr, name, dl, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %s  %-12s ♥%-5d ⭳%-6d %s%s" % (pid, abbr, likes, dl, name[:52], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    # Geriye uyumlu: eski cagri `printables-ara.py "<terim>" [max]` aynen calisir (derin=False).
    #  --tam-kelime : baslikta markayi TAM KELIME arar (alt-dize gurultusunu eler).
    #  --derin      : keeper-cap'i KALDIR, ham havuzu (offset<3000 tavanina/total'a kadar) TAM tara.
    #                 derin modda pozisyonel sayi = OPSIYONEL cikis-trim (verilmezse tum havuz).
    args = sys.argv[1:]
    tam_kelime = "--tam-kelime" in args
    derin = "--derin" in args
    pos = [a for a in args if a not in ("--tam-kelime", "--derin")]
    if not pos:
        sys.exit('Kullanim: python3 tools/printables-ara.py "<marka/terim>" [max] [--tam-kelime] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, tam_kelime=tam_kelime, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 250, tam_kelime=tam_kelime)
