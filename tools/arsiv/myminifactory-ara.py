#!/usr/bin/env python3
# EMEKLI - Okan 19 Tem: bu platformda arama YAPILMAZ (parity-backfill'den cikarildi).
"""MyMiniFactory'de MARKA/terim arar; sitede OLMAYAN + satilabilir + gurultusuz + MARKA-ALAKALI
obje ID'lerini verir. MakerWorld'teki makerworld-ara.py'nin MMF esdegeri.

Kullanim:  python3 tools/myminifactory-ara.py "Renault" [max]
   -> aday obje ID'lerini bir satirda (bosluk ayirli) yazar + id/lisans/baslik listesi basar.

ELER:  * satilamaz lisans (satilabilir() FAIL-CLOSED — Standard/Exclusive/NC/bilinmeyen) VE
         (varsa) licenses[] flag'i commercial-use=false / store=true / exclusivity=true ise
       * anahtarlik/logo/amblem/minyatur/kit-card gurultusu (COP listesi)
       * \\bMARKA\\b KELIME-SINIRI: printables-api.marka_kelime_gecer() (ORTAK filtre — inline
         DEGIL, import). Marka adi baslik/etiket/url'de TAM KELIME degilse ele (Oxford/afford eler,
         Ford gecer; Turkce-duyarli).
       * `.urun-kaynaklari.json`'da zaten kayitli MMF obje ID'leri (dedup)

ANAHTAR GEREKIR (MMF API). Anahtar yoksa net rapor basar (uydurma yok). Sir icermez.
"""
import importlib.util, os, re, sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mmf = _load("myminifactory_api", "myminifactory-api.py")
# ORTAK \bMARKA\b filtresi — inline etme, printables-api.py'den import et (spec geregi).
pa = _load("printables_api", "printables-api.py")


def marka_geciyor(marka, *metinler):
    r"""marka, verilen metinlerden en az birinde TAM KELIME olarak geciyor mu?
    ORTAK printables-api.marka_kelime_gecer(baslik, marka) uzerine kurulu (her metin icin dener).
    'ford' -> 'Ford Mustang' EVET; 'Oxford'/'afford' HAYIR."""
    return any(pa.marka_kelime_gecer(t or "", marka) for t in metinler)


def mevcut_idler():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        # https://www.myminifactory.com/object/<slug>-<id>  ya da  /object/<id>
        for m in re.findall(r'myminifactory\.com/object/(?:[^"/]*?-)?(\d+)', blob):
            ids.add(m)
        # ic anahtar bicimleri: "mmf12345", mmf:12345, mmf/12345
        for m in re.findall(r'mmf[:/]?(\d{3,})', blob, re.I):
            ids.add(m)
    return ids


def main(term, maxn, derin=False, cikis_limiti=None):
    """term/marka ara, sitede OLMAYAN uygun aday obje ID'lerini bas.

    Sayfalama (pagination) ile keeper-cap AYRI (2026-07-18 duzeltme; thing-ara.py deseni):
      - derin=False (varsayilan, GERIYE-UYUMLU): dongu `maxn` keeper toplayinca DURUR (eski davranis).
      - derin=True (--derin): `maxn` dongoyu DURDURMAZ; ham havuz IKINCIL tavana (page<=100) ya da
        `total` tukenene kadar TAM taranir. Boylece uygun havuz erken kesilmez.
    `cikis_limiti` (opsiyonel): siralamadan sonra cikti listesini kirpar (None=kirpma yok)."""
    try:
        mmf.require_key()
    except mmf.MMFNoKey as e:
        print("ANAHTAR YOK:", e)
        print("\nIDLER (talep sirasi):")   # bos — orkestrator/insan icin tutarli cikti
        return

    mevcut = mevcut_idler()
    bulunan, elenen_cop, elenen_nc, elenen_marka = [], [], [], []
    seen = set()
    page, total = 1, None
    PER = 30
    # DONGU KOSULU: derin modda maxn'e bakma (havuzu ikincil tavana kadar tam gez); degilse eski cap.
    while page <= 100 and (derin or len(bulunan) < maxn):
        try:
            res = mmf.search(term, per_page=PER, page=page)
        except Exception as e:                                   # noqa: BLE001
            print("ARAMA HATA (page %d):" % page, e); break
        total = res.get("total_count") if total is None else total
        items = res.get("items") or []
        if not items:
            break
        for h in items:
            pid = str(h.get("id"))
            if pid in seen:
                continue
            seen.add(pid)
            if pid in mevcut:
                continue
            name = (h.get("name") or "").replace("\n", " ")
            url = h.get("url") or ""
            tags = " ".join(h.get("tags") or [])
            lic = h.get("license") or ""
            flags = mmf.ticari_flags(h.get("licenses"))
            views = h.get("views") or 0
            likes = h.get("likes") or 0
            # satilamaz -> populerlik DELMEZ (lisans string kapisi + flag capraz reddi)
            if not mmf.satilabilir(lic) or flags is False:
                elenen_nc.append((pid, lic, name)); continue
            # \bMARKA\b tam-kelime alaka testi (baslik + etiket + url)
            if not marka_geciyor(term, name, tags, url):
                elenen_marka.append((pid, name)); continue
            pop = mmf.populer(views, likes)
            if mmf.is_nobypass(name):
                elenen_cop.append((pid, name)); continue         # logo/amblem/merch -> hep ele
            if mmf.is_cop(name) and not pop:
                elenen_cop.append((pid, name)); continue         # cop VE populer degil -> ele
            bulunan.append((pid, lic, name, views, likes, mmf.is_cop(name)))
            # keeper-cap SADECE derin-olmayan (eski) modda dongoyu keser
            if not derin and len(bulunan) >= maxn:
                break
        page += 1
        if total and (page - 1) * PER >= total:
            break

    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, views) azalan
    havuz_toplam = len(bulunan)   # kirpmadan ONCE toplanan gercek aday sayisi (kabul olcumu)
    if cikis_limiti is not None:
        bulunan = bulunan[:cikis_limiti]

    if elenen_nc:
        print("--- SATILAMAZ elenen %d (Standard/Exclusive/NC/bilinmeyen — populerlik DELMEZ) ---" % len(elenen_nc))
        for pid, lic, name in elenen_nc[:15]:
            print("  x %-9s %-34s %s" % (pid, ("[" + str(lic)[:32] + "]"), name[:46]))
    if elenen_marka:
        print("--- MARKA-ALAKASIZ elenen %d (\\b%s\\b tam kelime degil) ---" % (len(elenen_marka), term))
        for pid, name in elenen_marka[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur/kit-card; populer OLMAYAN) ---" % len(elenen_cop))
        for pid, name in elenen_cop[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[5])
    kirpma = "" if cikis_limiti is None else " (cikis %d'e kirpildi; havuz %d)" % (len(bulunan), havuz_toplam)
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, satilamaz %d, "
          "marka-alakasiz %d, cop %d elendi; populer-cop ISTISNA %d)%s ==="
          % (term, len(bulunan), total, len(mevcut & seen), len(elenen_nc),
             len(elenen_marka), len(elenen_cop), pop_cop, kirpma))
    for pid, lic, name, views, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %-9s %-14s ♥%-5d 👁%-7d %s%s" % (pid, str(lic)[:14], likes, views, name[:48], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    # Geriye uyumlu: eski cagri `myminifactory-ara.py "<terim>" [max]` aynen calisir (derin=False).
    #  --derin : keeper-cap'i KALDIR, ham havuzu (page<=100 tavanina/total'a kadar) TAM tara.
    #            derin modda pozisyonel sayi = OPSIYONEL cikis-trim (verilmezse tum havuz).
    args = sys.argv[1:]
    derin = "--derin" in args
    pos = [a for a in args if a != "--derin"]
    if not pos:
        sys.exit('Kullanim: python3 tools/myminifactory-ara.py "<marka/terim>" [max] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 250)
