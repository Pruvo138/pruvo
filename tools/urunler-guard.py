#!/usr/bin/env python3
"""urunler-guard.py — urunler.json icin OTONOM, self-healing koruma katmani.

AMAC: toplu urun ekleme sirasinda MEVCUT (HEAD'de zaten var olan) urunlerin
kazayla bozulmasini YAPISAL olarak imkansiz kilmak. Guard kimseye ONAY SORMAZ;
deterministik bir kuralla calisir ve sessizce dogru olani yapar (self-heal).

KURAL — working-tree urunler.json'i `git show HEAD:urunler.json` ile karsilastirir:
  * HEAD'de OLMAYAN id (yeni urun)                 -> SERBEST, hic dokunma.
  * HEAD'de OLAN bir urunun alan(lar)i degismisse:
      - degisen alanlarin TAMAMI .urunler-duzelt-izin.json manifestinde o id
        icin (ayni deger ile) beyan edilmisse        -> KABUL (mesru duzeltme).
      - aksi halde                                    -> urunun TUM alanlarini
        HEAD'deki haline yerinde geri dondur (self-heal).
  * HEAD'de olup working-tree'den SILINMIS urun:
      - id .urunler-sil-izin.json manifestinde beyan edilmisse -> KABUL
        (yetkili silme; or. yanlislikla eklenmis logo/telif riskli urun).
      - aksi halde (izinsiz)                            -> geri ekle (koru).

Manifest DEGER-BAGLI'dir: bir alanin degisimine ancak working-tree'deki yeni
deger, manifeste yazilan beklenen deger ile birebir esitse izin verilir. Bu
sayede eski/bayat bir manifest asla yeni bir kazayi mesrulastiramaz (yalnizca
zaten commit'lenmis degeri "yeniden" onaylar, ki o da HEAD ile esit oldugundan
degisim sayilmaz). Silme manifesti id-listesidir (deger-bagli degildir — silme
ikili bir eylemdir). Guard manifestleri ASLA SILMEZ (bkz. post-commit hook);
iki kez pes pese calismasi idempotenttir.

Tum okuma/yazma .urunler.lock flock'u altinda yapilir (printables-ekle.py deseni).
Ne yaptigini .urunler-guard.log'a yazar. Cikis kodu DAIMA 0 — asla commit/push'u
bloklamaz; bozugu ENGELLEMEZ, DUZELTIR.

Kullanim:  python3 tools/urunler-guard.py [--tetik commit|push|manuel]
"""
import argparse
import copy
import datetime
import fcntl
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
MANIFEST = os.path.join(ROOT, ".urunler-duzelt-izin.json")
MANIFEST_SIL = os.path.join(ROOT, ".urunler-sil-izin.json")
LOG = os.path.join(ROOT, ".urunler-guard.log")

_MISSING = object()


def _log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("[%s] %s\n" % (ts, msg))
    except OSError:
        pass


def _git(*args):
    """git -C ROOT <args> -> (rc, stdout_bytes). Hata yutulur."""
    try:
        p = subprocess.run(["git", "-C", ROOT, *args],
                           capture_output=True)
        return p.returncode, p.stdout
    except Exception:
        return 1, b""


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _atomic_write(path, obj):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _changed_fields(head_p, wt_p):
    """head_p ve wt_p arasinda farkli olan alan adlari."""
    out = []
    for k in set(head_p) | set(wt_p):
        a = head_p.get(k, _MISSING)
        b = wt_p.get(k, _MISSING)
        if a is _MISSING or b is _MISSING:
            if not (a is _MISSING and b is _MISSING):
                out.append(k)
            continue
        if _canon(a) != _canon(b):
            out.append(k)
    return out


def _authorized(uid, field, wt_p, manifest):
    """wt_p[field] degisimi manifestte (ayni deger ile) beyan edilmis mi?"""
    entry = manifest.get(uid)
    if not isinstance(entry, dict) or field not in entry:
        return False
    if field not in wt_p:  # WT'de silinmis alan -> deger-bagli izin veremez
        return False
    return _canon(wt_p[field]) == _canon(entry[field])


def heal(tetik):
    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        # HEAD:urunler.json — protun temel (dogru) hali.
        rc, head_bytes = _git("show", "HEAD:urunler.json")
        if rc != 0:
            _log("%s: HEAD:urunler.json okunamadi (yeni repo / izlenmiyor?) — atlandi." % tetik)
            return
        try:
            head_list = json.loads(head_bytes.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            _log("%s: HEAD:urunler.json cozumlenemedi — atlandi." % tetik)
            return

        # Working-tree urunler.json — commit edilmek uzere olan hal.
        try:
            with open(URUNLER, encoding="utf-8") as f:
                wt_list = json.load(f)
        except FileNotFoundError:
            _log("%s: working-tree urunler.json yok — atlandi." % tetik)
            return
        except ValueError:
            # Bozuk JSON'i HEAD'e sifirlamak tum yeni urunleri silerdi; guvenli
            # degil. Bloklamayiz ama gorunur sekilde uyariyi log'a yazariz.
            _log("%s: UYARI working-tree urunler.json BOZUK JSON — guard mudahale ETMEDI." % tetik)
            return

        manifest = {}
        if os.path.exists(MANIFEST):
            try:
                with open(MANIFEST, encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict):
                    manifest = m
            except ValueError:
                _log("%s: UYARI manifest bozuk — izin YOK sayildi." % tetik)

        sil_izin = set()
        if os.path.exists(MANIFEST_SIL):
            try:
                with open(MANIFEST_SIL, encoding="utf-8") as f:
                    s = json.load(f)
                if isinstance(s, list):
                    sil_izin = set(s)
            except ValueError:
                _log("%s: UYARI silme manifesti bozuk — izin YOK sayildi." % tetik)

        head_by_id = {}
        for p in head_list:
            if isinstance(p, dict) and "id" in p:
                head_by_id[p["id"]] = p

        restored, kept_auth = [], []
        yeni = 0
        wt_ids = set()

        # 1) Working-tree sirasini KORU; mevcut urunleri yerinde denetle.
        for i, p in enumerate(wt_list):
            if not isinstance(p, dict) or "id" not in p:
                continue
            uid = p["id"]
            wt_ids.add(uid)
            head_p = head_by_id.get(uid)
            if head_p is None:
                yeni += 1
                continue  # yeni urun — serbest
            changed = _changed_fields(head_p, p)
            if not changed:
                continue  # degismemis
            unauth = [c for c in changed if not _authorized(uid, c, p, manifest)]
            if unauth:
                wt_list[i] = copy.deepcopy(head_p)  # TUM alanlari geri al
                restored.append((uid, sorted(changed)))
            else:
                kept_auth.append((uid, sorted(changed)))

        # 2) Izinsiz SILINEN mevcut urunleri geri ekle (varsayilan koru);
        #    .urunler-sil-izin.json'da beyan edilenler yetkili sayilir, geri EKLENMEZ.
        eksik = [uid for uid in head_by_id if uid not in wt_ids]
        silinen = [uid for uid in eksik if uid not in sil_izin]
        yetkili_silme = [uid for uid in eksik if uid in sil_izin]
        for uid in silinen:
            wt_list.insert(0, copy.deepcopy(head_by_id[uid]))

        degisti = bool(restored or silinen)

        if degisti:
            _atomic_write(URUNLER, wt_list)
            # Index'te de urunler.json stage edilmisse healed hali ile guncelle
            # ki `git add <dosya>; git commit` akisinda commit temiz olsun.
            rc, staged = _git("diff", "--cached", "--name-only")
            if rc == 0 and "urunler.json" in staged.decode("utf-8", "replace").split():
                _git("add", "urunler.json")

        # Ozet log
        parts = ["%s: yeni=%d" % (tetik, yeni)]
        if restored:
            parts.append("GERI_YUKLENEN=%d %s" % (
                len(restored),
                ", ".join("%s[%s]" % (u, ",".join(fs)) for u, fs in restored[:40])))
        if silinen:
            parts.append("SILINMISTEN_GERI=%d %s" % (len(silinen), ", ".join(silinen[:40])))
        if kept_auth:
            parts.append("mesru_duzeltme=%d %s" % (
                len(kept_auth),
                ", ".join("%s[%s]" % (u, ",".join(fs)) for u, fs in kept_auth[:40])))
        if yetkili_silme:
            parts.append("yetkili_silme=%d %s" % (len(yetkili_silme), ", ".join(yetkili_silme[:40])))
        if not (restored or silinen or kept_auth or yetkili_silme):
            parts.append("mudahale=YOK")
        _log(" | ".join(parts))
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tetik", default="manuel",
                    help="tetikleyen baglam: commit|push|manuel")
    args = ap.parse_args()
    try:
        heal(args.tetik)
    except Exception as e:  # guard ASLA commit/push'u dusurmez
        _log("%s: BEKLENMEDIK HATA %r — bloklamadan cikildi." % (args.tetik, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
