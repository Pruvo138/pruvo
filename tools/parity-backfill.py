#!/usr/bin/env python3
"""PARITY BACKFILL surucusu — Codex-YARGI kapili (Sonnet YOK, minimal Opus).

Akis her (marka, platform) icin:
  <platform>-ara.py <marka>   -> aday (id,ad) listesi (NC/dup/marka-alakasiz ZATEN elenmis)
  CODEX YARGI (parity-yargi)  -> ad bazli sinif: GERCEK PARCA tut / maket-merch-IP at
                                 (ara.py'nin KACIRDIGI olcekli-maket/logo-anahtarligi eler)
  <platform>-ekle.py <keep>   -> STAGE (lisans fail-closed + Codex icerik + R2 + urunler.json flock)
  marka-kapsama.py kaydet      -> parity defteri
Icerik/gorsel + yargi = Codex (kota-disi). Surucu dongu = 0 Claude alt-ajani.
COMMIT ETMEZ — mimar sonra denetim-kapisi + parti/mukerrer-kontrol + publish.

Kullanim:
  python3 parity-backfill.py --yargi-test <Platform> <marka>            # YAZMA YOK: ara+yargi, karar bas
  python3 parity-backfill.py --havuz-test <Platform> <marka> [--derin]  # YAZMA/CODEX YOK: havuz boyu olc
  python3 parity-backfill.py <Platform> <marka1,marka2|GAP> [per_max] [bekle] [--derin]

--derin: adaptore --derin gecirir -> per_max keeper-cap KALKAR, ham havuz TAM taranir
         (offset<3000 / page<=100 ikincil tavana kadar) ve tumu Codex-yargi kapisina gider.
         --derin YOKSA eski davranis birebir (per_max=50 keeper'da durur).
"""
import json
import importlib.util
import os
import re
import subprocess
import sys
import time

ROOT = "/Users/okan/dev/pruvo"
# Arama/ekle/kapsama scriptlerini BU dosyanin YANINDAN cagir (worktree kopyasi kendi
# adaptorlerini gorsun; adaptorler zaten cekirdegini `_HERE`'den yukluyor). main'e merge
# edilince == ROOT/tools, davranis ayni; worktree'de ise worktree adaptorleri kosar.
TOOLS = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex"
DEFTER = os.path.join(ROOT, ".marka-kapsama.json")
URUNLER = os.path.join(ROOT, "urunler.json")
SCRATCH = os.path.dirname(os.path.abspath(__file__))
RAPOR = os.path.join(ROOT, ".thing-cache", "parity-backfill-rapor.json")

_HERE = os.path.dirname(os.path.abspath(__file__))
_PR_SPEC = importlib.util.spec_from_file_location("pr_api", os.path.join(_HERE, "printables-api.py"))
pr = importlib.util.module_from_spec(_PR_SPEC)
_PR_SPEC.loader.exec_module(pr)

PLAT = {
    "MakerWorld": ("makerworld-ara.py", "makerworld-ekle.py"),
    "MyMiniFactory": ("myminifactory-ara.py", "myminifactory-ekle.py"),
    "Thingiverse": ("thing-ara.py", "urun-ekle.py"),
    "Printables": ("printables-ara.py", "printables-ekle.py"),
    "********": ("cgt-ara.py", "cgt-ekle.py"),
}

# `--derin` bayragini destekleyen ara adaptorleri (keeper-cap'i havuzdan ayirir; 2026-07-18).
# Bu sette olan platformlar icin derin modda per_max KALDIRILIR -> TUM ham havuz yargiya gider.
DERIN_DESTEK = {"Thingiverse", "Printables", "MakerWorld", "MyMiniFactory", "********"}

YARGI_SEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "keep": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "keep", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

_KEEP_REAL = (
    "bracket", "braket", "spacer", "gear", "disli", "mount", "holder",
    "adapter", "adaptor", "clip", "klips", "knob", "tutucu", "support",
)
_FIREARM = (
    "m-lok", "mlok", "magpul", "moe grip", "moe stock", "ctr stock",
    "magwell", "cheek riser", "cheek-riser", "pistol brace", "pistol-brace",
    "picatinny", "handguard", "ar-15", "ar15", "buffer tube",
    "lower receiver", "upper receiver", "pmag",
)


def _blob(name):
    return " " + pr.tr_lower(name or "") + " "


def _is_firearm(name):
    n = _blob(name)
    return any(term in n for term in _FIREARM)


def _is_keep_default(name):
    n = _blob(name)
    if "airsoft" in n or "softair" in n:
        return True, "airsoft hobi replika"
    if pr.is_logo(name) or pr.is_merch(name) or " text" in n or " sign" in n:
        return False, "logo-merch"
    if _is_firearm(name):
        return False, "clear firearm aksesuar"
    if any(term in n for term in _KEEP_REAL):
        return True, "gercek/ambiguous parca; keep-by-default"
    return None, ""


def _defter():
    if os.path.exists(DEFTER):
        with open(DEFTER, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _urun_sayisi():
    with open(URUNLER, encoding="utf-8") as f:
        return len(json.load(f))


def _gap(d, marka, pl):
    k = d.get(marka, {}).get(pl)
    return not (k and (k.get("eklenen", 0) > 0 or k.get("taranan", 0) > 0))


def gap_markalar(platform):
    d = _defter()
    return sorted(m for m in d if _gap(d, m, platform))


def _parse_taranan(out):
    m = re.search(r"toplam eslesme (\d+)", out)
    return int(m.group(1)) if m else 0


def _parse_ids(out):
    """Sonda 'IDLER'/'SLUGLAR (talep sirasi...):' satirindan sonraki tam-id listesi."""
    lines = out.splitlines()
    for i, l in enumerate(lines):
        if ("IDLER" in l or "SLUGLAR" in l) and "talep sirasi" in l:
            return lines[i + 1].split() if i + 1 < len(lines) else []
    # yedek: son bosluk-ayrik id benzeri satir
    for l in reversed(lines):
        s = l.strip()
        if s and " " in s and not any(c in s for c in "=♥⭳👁#") and all(len(t) > 2 for t in s.split()[:2]):
            return s.split()
    return []


def _parse_adlar(out, ids):
    """Aday tablosundan AD listesi cek; SLUGLAR/IDLER tam-id'leriyle SIRAYLA eslestir (ayni 'bulunan' sirasi).
    Tablo id'si kirpik olabilir -> isim tablodan, tam id SLUGLAR'dan; ikisi de ayni sirada.
    Ikinci metrik emojisi platforma gore degisir: Cults3D/MMF/MakerWorld ⭳/👁, Thingiverse ⚒."""
    adlar = []
    for l in out.splitlines():
        # aday satiri: '  <id> ... ♥N <emoji>N <ad>'  (elenen satirlari 'x ' ile baslar, atla)
        m = re.search(r"[♥]\s*\d[\d.,]*\s+[⭳👁⚒]\s*\d[\d.,]*\s+(.+?)\s*(★POPULER-COP)?\s*$", l)
        if m and not l.lstrip().startswith("x "):
            adlar.append(m.group(1).strip())
    if len(adlar) == len(ids):
        return adlar
    return None  # hizalama guvensiz -> ad yok


def codex_yargi(brand, pairs):
    """pairs=[(id,ad)]. Codex ad bazli sinif -> ({keep_id}, {id:reason}). Codex patlarsa ({},{}) (guvenli: ekleme)."""
    if not pairs:
        return set(), {}
    liste = "\n".join("%d. %s: %s" % (i + 1, pid, ad or "(ad yok)") for i, (pid, ad) in enumerate(pairs))
    prompt = (
        "Sen bir 3D-baski yedek-parca magazasi kuratorusun. Marka: %s.\n"
        "Asagidaki adaylari SATILABILIR GERCEK ISLEVSEL PARCA mi yoksa YASAK/alakasiz mi diye sinifla.\n\n"
        "TUT (keep=true): markanin gercek islevsel parcasi/aksesuari — braket, spacer, mount, gear, "
        "tutucu, adaptor, klips, muhafaza, yedek parca. SUREKLI KURAL: belirsizde TUT; "
        "gercek parca marka LOGOSU tasisa da TUT.\n"
        "AT (keep=false):\n"
        "- olcekli model / maket / diorama / vitrin-modeli / diecast / RC govde-kabugu / '1:24' '1/76' "
        "'scale model' 'model v1' gibi ARAC MAKETI (YASAK sinif).\n"
        "- clear firearm accessories: M-LOK, Magpul, MOE/CTR stock-grip, magwell, picatinny, handguard, "
        "AR-15/AR15, buffer tube, receiver, pistol brace.\n"
        "- airsoft/softair replika parcalari HARIC gercek atesli silah aksesuarları.\n"
        "- logo-merch: urunun KENDISI logo/amblem/rozet/plaket/anahtarlik/kurabiye-kalibi olan.\n"
        "- ucuncu-taraf IP (film/oyun/Disney/Marvel vb.).\n"
        "- markayla alakasiz, belirsiz ya da cop (adi sadece marka adi olan bos kayit).\n\n"
        "Adaylar (id: ad):\n%s\n\n"
        "Her id icin keep(true/false) + kisa Turkce gerekce dondur. SADECE listedeki id'ler."
        % (brand, liste)
    )
    sema_p = os.path.join(SCRATCH, "_yargi-sema.json")
    with open(sema_p, "w", encoding="utf-8") as f:
        json.dump(YARGI_SEMA, f)
    out_p = os.path.join(SCRATCH, "_yargi-out.json")
    try:
        if os.path.exists(out_p):
            os.remove(out_p)
    except OSError:
        pass
    try:
        r = subprocess.run(
            [CODEX, "exec", "-m", "gpt-5.4-mini", "-c", "model_reasoning_effort=low",
             "-s", "read-only", "--skip-git-repo-check",
             "--output-schema", sema_p, "-o", out_p, prompt],
            capture_output=True, text=True, timeout=300)
        raw = ""
        if os.path.exists(out_p):
            with open(out_p, encoding="utf-8") as f:
                raw = f.read()
        if not raw.strip():
            raw = r.stdout or ""
        data = json.loads(raw)
        res = data.get("results", [])
        gecerli = {p[0] for p in pairs}
        keep = {x["id"] for x in res if x.get("keep") and x.get("id") in gecerli}
        reason = {x["id"]: x.get("reason", "") for x in res}
        for pid, ad in pairs:
            pol, why = _is_keep_default(ad)
            if pol is True:
                keep.add(pid)
                reason[pid] = why
            elif pol is False:
                keep.discard(pid)
                reason[pid] = why
        # yargida gorunmeyen id -> guvenli varsayilan AT (ekleme); policy True ise keep'e eklenir.
        return keep, reason
    except Exception as e:
        return None, {"_hata": str(e)[:200]}


def _ara(platform, marka, per_max, derin=False):
    ara_s = PLAT[platform][0]
    cmd = [PY, os.path.join(TOOLS, ara_s), marka]
    if derin and platform in DERIN_DESTEK:
        cmd.append("--derin")        # ham havuzu TAM tara; per_max trim'i YOK -> tum havuz yargiya
    else:
        cmd.append(str(per_max))     # eski davranis: sig cap (per_max keeper'da dur)
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=(1800 if derin else 420))
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    ids = _parse_ids(out)
    adlar = _parse_adlar(out, ids)
    pairs = list(zip(ids, adlar)) if adlar else [(i, None) for i in ids]
    # THROTTLE: 429/Too Many Requests + aday YOK -> gercek bos DEGIL, retry gerekir.
    throttled = (("429" in out) or ("Too Many Requests" in out)) and not ids
    return out, ids, pairs, _parse_taranan(out), throttled


def yargi_test(platform, marka):
    print("YARGI-TEST (YAZMA YOK) | %s | %s" % (platform, marka))
    out, ids, pairs, taranan, _ = _ara(platform, marka, 12)
    print("aday %d (taranan %d):" % (len(ids), taranan))
    for pid, ad in pairs:
        print("  %-42s %s" % (pid, ad or "(ad yok)"))
    keep, reason = codex_yargi(marka, pairs)
    if keep is None:
        print("CODEX YARGI HATA: %s" % reason.get("_hata"))
        return
    print("\nKARAR:")
    for pid, ad in pairs:
        mark = "TUT " if pid in keep else "AT  "
        print("  %s %-42s %s" % (mark, pid, reason.get(pid, "")[:70]))
    print("\n-> TUT %d / AT %d" % (len(keep), len(ids) - len(keep)))


def havuz_test(platform, marka, derin):
    """YAZMA/CODEX YOK: sadece _ara havuzunu olc — sig-cap mi (eski) tam-havuz mu (derin) ispat.
    Kabul #3: derin yolun ham havuzu sig-cap'e DUSMEDIGINI kanitlar (parity-backfill entegrasyon)."""
    print("HAVUZ-TEST (YAZMA/CODEX YOK) | %s | %s | derin=%s" % (platform, marka, derin))
    out, ids, pairs, taranan, throttled = _ara(platform, marka, 50, derin=derin)
    if throttled:
        print("!!! 429 THROTTLE — havuz olculemedi (rate-limit). Reset sonrasi tekrar.")
    print("toplam eslesme(API)=%d | HAVUZ(aday)=%d | throttled=%s" % (taranan, len(ids), throttled))
    print("IDLER ilk-15:", " ".join(ids[:15]))


def _rapor_yol(platform):
    return os.path.join(ROOT, ".thing-cache", "parity-backfill-rapor-%s.json" % platform)


def _rapor_yaz(platform, toplam, rapor):
    yol = _rapor_yol(platform)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"platform": platform, "toplam_staged": toplam, "islenen": len(rapor),
                   "markalar": rapor}, f, ensure_ascii=False, indent=2)


def kos(platform, markalar, per_max, bekle, derin=False):
    ekle_s = PLAT[platform][1]
    rapor = []
    toplam_staged = 0
    ardisik_throttle = 0
    for n, marka in enumerate(markalar, 1):
        t0 = time.time()
        kayit = {"marka": marka, "platform": platform}
        try:
            out, ids, pairs, taranan, throttled = _ara(platform, marka, per_max, derin=derin)
            if throttled:
                ardisik_throttle += 1
                kayit["throttled"] = True
                rapor.append(kayit)
                _rapor_yaz(platform, toplam_staged, rapor)
                print("[%s %d/%d] %-22s 429 THROTTLE -> kaydet YOK (retry edilebilir; ardisik %d)"
                      % (platform, n, len(markalar), marka, ardisik_throttle), flush=True)
                if ardisik_throttle >= 3:
                    print("!!! 3 ardisik 429 -> DUR. Limit reseti sonrasi ayni komut (GAP) kaldigindan devam eder.", flush=True)
                    break
                time.sleep(max(bekle * 4, 30))
                continue
            ardisik_throttle = 0
            keep, reason = codex_yargi(marka, pairs)
            if keep is None:
                kayit.update({"taranan": taranan, "aday": len(ids), "staged": 0,
                              "atlandi": "codex-yargi-hata", "hata": reason.get("_hata")})
                print("[%s %d/%d] %-22s YARGI HATA -> atlandi" % (platform, n, len(markalar), marka), flush=True)
                rapor.append(kayit)
                _rapor_yaz(platform, toplam_staged, rapor)
                time.sleep(bekle)
                continue
            keep_ids = [i for i in ids if i in keep]
            atilan = [{"id": i, "gerekce": reason.get(i, "")} for i in ids if i not in keep]
            once = _urun_sayisi()
            staged = 0
            ekle_hata = ""
            if keep_ids:
                r2 = subprocess.run([PY, os.path.join(TOOLS, ekle_s)] + keep_ids,
                                    capture_output=True, text=True, timeout=5400)
                if r2.returncode != 0:
                    ekle_hata = (r2.stderr or "")[-400:]
                staged = _urun_sayisi() - once
            subprocess.run([PY, os.path.join(TOOLS, "marka-kapsama.py"), "kaydet",
                            "--marka", marka, "--platform", platform,
                            "--taranan", str(taranan), "--eklenen", str(staged),
                            "--elenen", str(max(0, taranan - staged))], capture_output=True, text=True)
            kayit.update({"taranan": taranan, "aday": len(ids), "tut": len(keep_ids),
                          "staged": staged, "atilan": atilan, "sn": round(time.time() - t0, 1)})
            if ekle_hata:
                kayit["ekle_hata"] = ekle_hata
            toplam_staged += staged
            print("[%s %d/%d] %-22s aday=%-3d tut=%-3d staged=%-3d (%.0fs)%s"
                  % (platform, n, len(markalar), marka, len(ids), len(keep_ids), staged,
                     time.time() - t0, "  ⚠EKLE-HATA" if ekle_hata else ""), flush=True)
        except Exception as e:
            kayit["hata"] = str(e)[:300]
            print("[%s %d/%d] %-22s HATA: %s" % (platform, n, len(markalar), marka, str(e)[:120]), flush=True)
        rapor.append(kayit)
        _rapor_yaz(platform, toplam_staged, rapor)
        time.sleep(bekle)
    print("\n=== BITTI: %s | %d marka | TOPLAM STAGED=%d ===" % (platform, len(rapor), toplam_staged), flush=True)
    print("Rapor: %s" % _rapor_yol(platform), flush=True)
    return toplam_staged


def main():
    a = sys.argv[1:]
    derin = "--derin" in a            # global bayrak: derin modda adaptore --derin gecir (tam havuz)
    a = [x for x in a if x != "--derin"]
    if a and a[0] == "--havuz-test":
        if len(a) < 3:
            sys.exit("Kullanim: parity-backfill.py --havuz-test <Platform> <marka> [--derin]")
        havuz_test(a[1], a[2], derin)
        return
    if a and a[0] == "--yargi-test":
        if len(a) < 3:
            sys.exit(__doc__)
        yargi_test(a[1], a[2])
        return
    if len(a) < 2:
        sys.exit(__doc__)
    platform = a[0]
    if platform not in PLAT:
        sys.exit("Platform: %s" % ", ".join(PLAT))
    arg = a[1]
    per_max = int(a[2]) if len(a) > 2 else 50
    bekle = int(a[3]) if len(a) > 3 else 8
    markalar = gap_markalar(platform) if arg == "GAP" else [m.strip() for m in arg.split(",") if m.strip()]
    print("PARITY BACKFILL | %s | %d marka | per_max=%d | bekle=%ds | derin=%s"
          % (platform, len(markalar), per_max, bekle, derin), flush=True)
    kos(platform, markalar, per_max, bekle, derin=derin)


if __name__ == "__main__":
    main()
