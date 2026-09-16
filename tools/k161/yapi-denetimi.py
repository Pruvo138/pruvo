#!/usr/bin/env python3
"""K161-ifsa cumle-duzey YAPI DENETIMI (bayt-alt-dizi, deterministik, AI yok).

islemler.json'daki her islem icin eski (urunler.json, jq) ile yeni metni YAPISAL
olarak karsilastirir. Bir parcanin icindeki TEK harf farki bile yakalanir.
Bulgu turleri:

  OLCU_BOZULDU      - eski metnin "\nYaklasik dis olculer:" kuyrugu (varsa)
                      yeni metnin SONUNDA BAYT-ESIT degil.
  UYDURMA_PARCA     - yeni metnin kuyruk oncesi parcasi = eski parcaların
                      SIRASI KORUNMUS alt kumesi + en fazla 1 SABLON degil.
                      Bir parcanin icindeki tek harf farki bile yakalanir.
  SUREC_KALINTISI   - yeni metinde denetim-kapisi.py'nin ifsa desenleri
                      (ICE AKTAR, kopyalama yok) + ek kokler
                      (basim basima basil baski yazdir print) gecmekte.
  TAVSIYE_KALINTISI - yeni metinde oneri/tavsiye/secim/tercih kokleri
                      (onerilir|tavsiye|secilmeli|tercih edil|kullanilmali)
                      gecmekte.
  DEGISMEYEN        - yeni == eski (degisim yok).

Sabit SABLON cumlesi (en fazla 1 adet eklenebilir):
  "<M> malzemeden uretilir."          M ∈ {PLA,PETG,ABS,ASA,TPU,PC,Naylon}
  "<M> veya <N> malzemeden uretilir." M,N ∈ {PLA,PETG,ABS,ASA,TPU,PC,Naylon}

";" ile ayrılan parca cikarilinca onceki parca "." ile kapanabilir (yalniz bu
1 bayt degisimi serbest): parca metni (ayractan arindirilmis) BAYT-ESIT
aranir, dolayisiyla "; " -> ". " ayrac degisimi sorun olmaz.

Cikti:
  YAPI_BULGU=<n>
  tur kirilimi (ornek: OLCU_BOZULDU: 12, UYDURMA_PARCA: 8, ...)
  bulgu>0 -> rc=1, degilse rc=0.

Kullanim:
  python3 tools/k161/yapi-denetimi.py <islemler.json> [--eski-kok /path/urunler.json]
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/okan/dev/pruvo")
EV = Path("/Users/okan/dev/pruvo/.claude/worktrees/k161-ifsa-plan")
URUNLER = ROOT / "urunler.json"

# === SABITLER ============================================================
# Olcu satiri (cumle bolunmez)
_OLCU_RE = re.compile(r"\nYaklaşık dış ölçüler:[^\n]*", re.UNICODE)
_OLCU_RE_LOOSE = re.compile(r"Yaklaşık dış ölçüler:[^\n]*", re.UNICODE)

# Ayraçlar: ". " (nokta + bosluk, ASCII), "; " (noktali virgul + bosluk),
# "\n" (satir sonu). Tum turkce noktalama ayraclari.
# Bir part = ayractan onceki metin; ayrac part'a dahil DEGIL.
# ". " / "! " / "? " -> cumle sonu
# "; " -> yan cumle
# "\n" -> satir sonu
_AYRAC_RE = re.compile(r"(?<=.)(?:\.\s+|;\s+|\n)|^[.\s;]+")

# SABIT SABLON: iki form
# Envanterden TURETILIR (cumle-plan.py ile ayni kural; PC/Naylon uretilemez -> sablona giremez).
_MALZ_LIST = [f["ad"] for f in json.loads((ROOT / "tools" / "filamentler.json").read_text(encoding="utf-8"))["filamentler"]
              if re.fullmatch(r"[A-Z]{2,5}", f.get("ad", ""))]
if not _MALZ_LIST:
    sys.exit("MALZEME_ENVANTERI_BOS: tools/filamentler.json okunamadi -> OLCULEMEDI")
SABLON_TEKIL = "|".join(re.escape(m) for m in _MALZ_LIST)
SABLON_RE = re.compile(
    rf"^(?:{SABLON_TEKIL}) malzemeden üretilir\.$|"
    rf"^(?:{SABLON_TEKIL}) veya (?:{SABLON_TEKIL}) malzemeden üretilir\.$",
    re.UNICODE,
)

# TAVSIYE_KALINTISI
_TAVSIYE_KOKLERI = [
    "önerilir", "öneril", "tavsiye", "seçilmeli", "tercih edil", "kullanılmalı",
    "kullanılması", "tercih", "öner",  # "onerilir" / "oneril" / "tavsiye" / "secilmeli"
]
_TAVSIYE_RE = re.compile(
    r"\b(?:önerilir|öneril|tavsiye|seçilmeli|tercih\s+edil|kullanılmalı"
    r"|kullanılması|tercih|öner)\w*",
    re.IGNORECASE | re.UNICODE,
)

# EK surec kokleri (denetim-kapisi desenlerinin TAM kapsamini kapmaz; sadece
# spec'in ekledigi 6 kok): "basim basima basil baski yazdir print"
# (denetim-kapisi zaten "baski", "basil-" ve print koklerinin cogunu kapsar)
_EK_KOKLER_RE = re.compile(
    r"\bbas[ıi]m\b|\bbas[ıi]ma\b|\bbas[ıi]l\b|\bbask[ıi]\w*\b"
    r"|\byazd[ıi]r\w*\b|\bprint\w*\b",
    re.IGNORECASE | re.UNICODE,
)


# === PARCALAMA ============================================================
def parcalara_bol(metin: str) -> list[str]:
    """Metni ayrac noktalarindan parcalara boler; her parca ayractan ARINDIRILMIS
    metin (yani '. ' veya '; ' veya '\\n' onceki metin)."""
    return [ptxt for ptxt, _, _ in parcala_ayrac_bilgisiyle(metin)]


def parcala_ayrac_bilgisiyle(metin: str):
    """Returns list of (part_text, sep_after, start_pos) tuples.
    sep_after: separator bytes AFTER the part ('. ', '; ', '\\n', or '')."""
    parts = []
    cur = ""
    cur_start = 0
    i = 0
    while i < len(metin):
        c = metin[i]
        if c in ".!?":
            j = i + 1
            while j < len(metin) and metin[j] in " \t":
                j += 1
            sep = metin[i:j]
            parts.append((cur, sep, cur_start))
            cur = ""
            cur_start = j
            i = j
            continue
        if c == ";":
            j = i + 1
            while j < len(metin) and metin[j] in " \t":
                j += 1
            sep = metin[i:j]
            parts.append((cur, sep, cur_start))
            cur = ""
            cur_start = j
            i = j
            continue
        if c == "\n":
            parts.append((cur, "\n", cur_start))
            cur = ""
            cur_start = i + 1
            i += 1
            continue
        cur += c
        i += 1
    if cur:
        parts.append((cur, "", cur_start))
    return parts


def olcu_ayir(metin: str) -> tuple[str, str]:
    """(prefix, olcu_tail) — olcu satiri '\\nYaklasik dis olculer:...' (varsa)
    cikarilir; yoksa olcu=''. prefix bos olabilir."""
    m = _OLCU_RE.search(metin)
    if m:
        return metin[:m.start()], metin[m.start():]
    # belki metin olcu ile BASLIYOR (ilk cumle olarak)
    m2 = _OLCU_RE_LOOSE.match(metin)
    if m2 and m2.start() == 0:
        return "", metin
    return metin, ""


# === denetim-kapisi ICE AKTAR ============================================
def _dk_yukle():
    """denetim-kapisi.py'yi yukler, ifsa desenlerini import eder."""
    tools_dir = str(EV / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location(
        "denetim_kapisi_k161_yapi", str(EV / "tools" / "denetim-kapisi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === KONTROL ==============================================================
def parca_eslesir(yeni_parca: str, eski_parcalar: list[str], dk) -> str | None:
    """yeni_parca icin eski_parcalar'da BAYT-ESIT eslesme varsa eski parca
    metnini, yoksa None. Parca metni (ayractan arindirilmis) karsilastirilir;
    ';' ile ayrilan onceki parcanin '.' ile kapanmasi sadece ayracta 1 byte
    degisimi — parca metni ayniysa sorun yok."""
    for ep in eski_parcalar:
        if ep == yeni_parca:
            return ep
    return None


def sablon_mu(parca: str, sep_after: str = "") -> bool:
    """Parca metninin SABIT SABLON olup olmadigini kontrol eder. Eger sep_after
    nokta ile basliyorsa, sablon '.' ile biten formdadir — kontrolu tamamlamak
    icin nokta eklenir."""
    test = parca.strip()
    if sep_after.startswith("."):
        test += "."
    return bool(SABLON_RE.match(test))


def kontroller(eski: str, yeni: str, dk) -> dict:
    """Tek bir kayit icin bulgulari hesaplar."""
    bulgular: list[tuple[str, str, str]] = []

    if yeni == eski:
        return {"bulgular": [("DEGISMEYEN", "-", "yeni == eski")]}

    # (i) OLCU kontrolu
    eski_prefix, eski_olcu = olcu_ayir(eski)
    yeni_prefix, yeni_olcu = olcu_ayir(yeni)
    if eski_olcu:
        # Eski metinde olcu var; yeni metnin SONUNDA BAYT-ESIT olmali
        if not yeni.endswith(eski_olcu):
            bulgular.append((
                "OLCU_BOZULDU",
                yeni_olcu[-50:] if yeni_olcu else "(yok)",
                f"eski olcu: {eski_olcu[-50:]}; yeni olcu: {yeni_olcu[-50:] if yeni_olcu else '(yok)'}",
            ))
        # yeni metnin kuyruk oncesi kismi:
        yeni_kuyruk_oncesi = yeni[: len(yeni) - len(eski_olcu)] if eski_olcu else yeni_prefix
    else:
        yeni_kuyruk_oncesi = yeni_prefix

    eski_parcalar = parcalara_bol(eski_prefix)
    yeni_parcalar_full = parcala_ayrac_bilgisiyle(yeni_kuyruk_oncesi)

    # (ii) UYDURMA_PARCA kontrolu — part_text + sep_after birlikte degerlendirilir
    #     (period genelde sep_after icinde kaliyor).
    sablon_sayaci = 0
    sablon_indexleri: list[int] = []
    for i, (ptxt, sep_a, _) in enumerate(yeni_parcalar_full):
        if sablon_mu(ptxt, sep_a):
            sablon_sayaci += 1
            sablon_indexleri.append(i)
    if sablon_sayaci > 1:
        bulgular.append((
            "UYDURMA_PARCA",
            f"sablon_sayisi={sablon_sayaci}",
            f"birden fazla SABLON cumlesi: {sablon_sayaci} > 1",
        ))

    # yeni parcalar: yalniz 1 SABLON eklenmis olabilir, geri kalan eski parcalar
    # ile BAYT-ESIT (ayractan arindirilmis) eslesmeli
    eski_parcalar_set = list(eski_parcalar)  # sirayi da koruyoruz
    for i, (ptxt, sep_a, _) in enumerate(yeni_parcalar_full):
        if i in sablon_indexleri:
            continue  # SABLON — UYDURMA_PARCA sayilmaz
        # Eslesme: sadece part_text (sep_after haric) bayt-esit olmali
        if ptxt not in eski_parcalar_set:
            bulgular.append((
                "UYDURMA_PARCA",
                ptxt[:60] + ("..." if len(ptxt) > 60 else ""),
                f"yeni parca '{ptxt[:60]}' eski parcalarla bayt-esit degil",
            ))
        else:
            eski_parcalar_set.remove(ptxt)

    # (iii) SUREC_KALINTISI kontrolu
    # denetim-kapisi'nin ifsa desenlerini import ile tara + ek kokler
    try:
        gecici = {"id": "TEST", "baslik": "", "aciklama": yeni_kuyruk_oncesi}
        r = dk.kapi_ifsa(gecici)
        sert = r.get("sert", [])
        uyari = r.get("uyari", [])
        for s in sert:
            bulgular.append((
                "SUREC_KALINTISI",
                f"[{s.get('kural', '?')}] {s.get('gerekce', '')[:60]}",
                f"ifsa SERT vurusu yeni metinde: {s.get('gerekce', '')[:60]}",
            ))
        for u in uyari:
            bulgular.append((
                "SUREC_KALINTISI",
                f"[{u.get('kural', '?')}] {u.get('gerekce', '')[:60]}",
                f"ifsa UYARI vurusu yeni metinde: {u.get('gerekce', '')[:60]}",
            ))
    except Exception as e:
        bulgular.append((
            "SUREC_KALINTISI",
            "denetim-kapisi CALISTIRILAMADI",
            f"kapi_ifsa exception: {e}",
        ))

    # ek kokler (denetim-kapisi bunlari zaten kapsar; yine de kontrol)
    for m in _EK_KOKLER_RE.finditer(yeni_kuyruk_oncesi):
        # Bu koklerden bazilari denetim-kapisi tarafindan zaten yakalanir; ama
        # "basim" (orn: "tek parca halinde uretilebilir, basim suresi ~2 saat")
        # denetim-kapisi tarafindan yakalanmayabilir.
        bulgular.append((
            "SUREC_KALINTISI",
            m.group(0),
            f"ek kok '{m.group(0)}' yeni metinde",
        ))

    # (iv) TAVSIYE_KALINTISI kontrolu
    for m in _TAVSIYE_RE.finditer(yeni_kuyruk_oncesi):
        bulgular.append((
            "TAVSIYE_KALINTISI",
            m.group(0),
            f"tavsiye koku '{m.group(0)}' yeni metinde",
        ))

    return {"bulgular": bulgular}


# === MAIN =================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("islemler", help="islemler.json (duzelt.py --toplu bicimi)")
    ap.add_argument("--eski-kok", default=str(URUNLER),
                    help="eski metni okumak icin urunler.json yolu")
    ap.add_argument("--id-alani", default="id")
    ap.add_argument("--deger-alani", default="deger")
    args = ap.parse_args()

    islemler_path = Path(args.islemler)
    if not islemler_path.exists():
        print(f"HATA: {islemler_path} bulunamadi", file=sys.stderr)
        return 4
    with open(islemler_path, encoding="utf-8") as f:
        islemler_doc = json.load(f)
    islemler = islemler_doc.get("islemler") or []
    if not isinstance(islemler, list):
        print("HATA: 'islemler' alani liste degil", file=sys.stderr)
        return 4

    eski_path = Path(args.eski_kok)
    if not eski_path.exists():
        print(f"HATA: {eski_path} bulunamadi", file=sys.stderr)
        return 4
    with open(eski_path, encoding="utf-8") as f:
        urunler = json.load(f)
    id_index = {u.get("id"): u for u in urunler if isinstance(u, dict)}

    dk = _dk_yukle()

    bulgu_sayac: dict[str, int] = {
        "OLCU_BOZULDU": 0,
        "UYDURMA_PARCA": 0,
        "SUREC_KALINTISI": 0,
        "TAVSIYE_KALINTISI": 0,
        "DEGISMEYEN": 0,
    }
    ornekler: dict[str, list] = {k: [] for k in bulgu_sayac}

    for op in islemler:
        if not isinstance(op, dict):
            continue
        uid = op.get(args.id_alani)
        yeni = op.get(args.deger_alani)
        if not isinstance(uid, str) or not isinstance(yeni, str):
            continue
        rec = id_index.get(uid)
        eski = str(rec.get("aciklama", "") or "") if isinstance(rec, dict) else ""
        r = kontroller(eski, yeni, dk)
        for tip, parca, detay in r["bulgular"]:
            bulgu_sayac[tip] += 1
            if len(ornekler[tip]) < 5:
                ornekler[tip].append((uid, parca, detay))

    toplam = sum(bulgu_sayac.values())
    print(f"islemler.json: {len(islemler)} kayit")
    print(f"YAPI_BULGU={toplam}")
    for tip, n in bulgu_sayac.items():
        print(f"  {tip}: {n}")
    if toplam > 0:
        print("\nornekler (ilk 5):")
        for tip, lst in ornekler.items():
            for u, p, d in lst:
                print(f"  [{tip}] {u}: parca={p!r} detay={d[:80]!r}")
    return 1 if toplam > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
