#!/usr/bin/env python3
# KraL sabah rutini — her gün 06:20'de cron ile koşar, o günün Tamirci spec'ini üretir.
# Kaynak-doğrusu: kutu + açık-kalem defteri + DEVAM + gh run list + git branch.
# Çıktı: ~/.claude/cron/tamirci-spec/KraL-Tamirci-<YYYYAAGG>.md
#
# Fail-loud: herhangi bir girdi okunamazsa o alan "OLCULEMEDI" olur VE rc=1 döner.
#
# ============================================================================
# 27 AĞU 2026 — `KraL-SabahTeslim-27Agu`: ÜÇ SINIF ONARIMI (tekil yama DEĞİL)
# ----------------------------------------------------------------------------
# ARIZA: cron 06:20'de `/usr/bin/python3` ile koştu, araç açılışta
#   `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
# ile düştü → o günün spec'i HİÇ ÜRETİLMEDİ ve kimse bunu görmedi.
#
# ① YORUMLAYICI VARSAYIMI KALDIRILDI (pin DEĞİL, KOD İNDİRİLDİ).
#    `X | None` / `tuple[list[dict], int]` gibi yazımlar annotation'ları
#    TANIM ANINDA değerlendirir; 3.9'da `type.__or__` yoktur → TypeError.
#    ÇARE `from __future__ import annotations`: TÜM annotation'lar dizgeye
#    döner, hiçbiri çalıştırma anında değerlendirilmez. Bu tek satır dosyadaki
#    HER annotation'ı — bugünküleri de yarın eklenecekleri de — kapsar; tek
#    satırı 3.9'a çevirmek yalnız BUGÜNKÜ yüzü kapatırdı.
#    🔴 CRONTAB'A DOKUNULMADI, gerekçe yazılı: (a) crontab satırının uzun yolu
#    ~100 karakterde kesen bilinen tuzağı var ([[crontab-uzun-yolu-keser]]),
#    (b) yorumlayıcıyı ÇİVİLEMEK varsayımı kaldırmaz, YERİNİ DEĞİŞTİRİR —
#    `/opt/homebrew/bin/python3` bir brew yükseltmesinde kaybolabilir ve arıza
#    BİREBİR geri gelir. Kod her iki yorumlayıcıda koşarsa varsayım YOK olur.
#
# ② VARSAYIM ÖLÇÜLÜYOR — VE ÖLÇÜT TEK KAYNAKTAN OKUNUYOR.
#    `--kendini-test` yorumlayıcı adlarını ELLE TAŞIMAZ: `crontab -l` içinden
#    bu betiği çağıran satırı bulup yorumlayıcıyı ORADAN okur (ikiz tanım YOK),
#    sonra aracı O yorumlayıcıyla `--ortam-testi` modunda FİİLEN çalıştırır.
#    Bugünkü arıza bu kolla ADIYLA düşerdi: `CAPRAZ_ORTAM=DUSTU`.
#    crontab okunamazsa `OLCULEMEDI` + rc≠0 (fail-closed).
#
# ③ 🔴 SONUÇ KOLU — ASIL KÖR NOKTA. Bugünkü arızayı gizleyen şey `rc` değildi;
#    kimse "spec ÜRETİLDİ Mİ" diye SORMUYORDU. Araç `rc=0` dönse bile dosya
#    yoksa bu bir ARIZADIR. `sonuc_kolu()` yazımdan SONRA diskten ölçer ve
#    `SONUC_KOLU=SPEC_URETILMEDI` basıp rc'yi yükseltir.
# ============================================================================
#
# Bayraklar:
#   --kuru          : dosya yazmaz, sadece özet satırı basar
#   --kendini-test  : iç sağlık + ÇAPRAZ ORTAM kontrolü; rc=0/1 ile çıkar (A1)
#   --ortam-testi   : modülü yükler, tek satır ortam raporu basar, çıkar
#   --spec-dizin D  : spec'in yazılacağı dizini değiştirir (A3 fikstürü)

from __future__ import annotations

import argparse
import ast
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

# ---- sabit yollar ----
KUTU = Path("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")
KALEMLER = Path("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md")
DEVAM = Path("/Users/okan/dev/pruvo/DEVAM.md")
REPO = Path("/Users/okan/dev/pruvo")
SPEC_DIR = Path.home() / ".claude/cron/tamirci-spec"

# ---- ORTAM SÖZLEŞMESİ (① + ②) ----
BU_BETIK = Path(os.path.abspath(__file__))

# ============================================================================
# 🔴 27 AĞU 2026 — `KraL-SabahYorumlayici-27Agu`: ASGARİ SÜRÜM ARTIK LİTERAL DEĞİL
# ----------------------------------------------------------------------------
# ESKİ HÂL: `ASGARI_SURUM = (3, 7)` — ELLE yazılmış bir sayı; gerekçesi yalnız
# üstündeki YORUM SATIRINDA duruyordu. Kusur bu evin tekrar eden sınıfının bir
# yüzü: bir yerde ÜRETİLEN değerin tüketicisi BAŞKA EKSENİ okur. Burada tüketici
# (`ortam_uyumlu`) "kodun gerçekten neye ihtiyacı var" sorusunu değil, "birinin
# bir gün yazdığı sayı" sorusunu okuyordu. Sonuç: dosyaya çalıştırma anında
# değerlendirilen bir `X | Y` ya da `match` girdiği anda literal 3.7'de KALIR,
# kol 3.9'da `UYUM=EVET` basar ve araç KENDİ ÇALIŞAMAYACAĞI sürümü ONAYLAR.
# 27 Ağu sabahı `kral-sabah.log`a düşen tam olarak buydu: TypeError'ın hemen
# ardından `ASGARI=3.7 UYUM=EVET`.
#
# YENİ HÂL: asgari sürüm KAYNAĞIN KENDİSİNDEN türetilir (AST taraması). Yarın
# eklenecek sözdizimi de kapsanır, çünkü ölçülen şey METNİN KENDİSİDİR.
# 🔴 FAIL-CLOSED: türetme yapılamıyorsa (kaynak okunamadı / bu yorumlayıcı
# kaynağı DERLEYEMİYOR) hüküm `ASGARI=OLCULEMEDI UYUM=HAYIR`dır — sessiz yeşil
# YOK. "Çalışamayacağım sürümde yeşil yakmak" bu kalemin ta kendisiydi.
#
# ⚠️ SINIR (bilerek yazıldı, iddia edilmiyor): bu tarama SÖZDİZİMİ eksenini
# ölçer, KÜTÜPHANE eksenini (`str.removeprefix`, `zoneinfo`, …) DEĞİL. Kütüphane
# sapması ② ÇAPRAZ ORTAM kolunun işidir — orada araç crontab'ın kendi
# yorumlayıcısıyla FİİLEN koşturulur.
# ============================================================================

# Sözdizimi-kapısı olmayan bir dosyanın tabanı: f-string (3.6).
_SURUM_TABANI = (3, 7)

# PEP 585 — yerleşik jenerikler (`list[int]`), 3.9.
_PEP585_ADLARI = ("list", "dict", "set", "frozenset", "tuple", "type")
# PEP 604 — `X | Y` yalnız BU adlar/`None` arasında görülürse tip birleşimi
# sayılır. Amaç yanlış-pozitifi kesmek: `bayrak | MASKE` bir tip ifadesi DEĞİL,
# ve yanlış-pozitif fail-closed kolu yüzünden aracı DURDURURDU.
_TIP_ADLARI = ("str", "int", "float", "bool", "bytes", "bytearray", "complex",
               "object", "list", "dict", "set", "frozenset", "tuple", "type",
               "Path", "Any")


def surum_dizgesi(vi=None) -> str:
    vi = vi or sys.version_info
    return "%d.%d.%d" % (vi[0], vi[1], vi[2])


def _annotation_dugumleri(agac):
    """Annotation BAĞLAMINDA duran düğümlerin kimlik kümesi.

    `from __future__ import annotations` YALNIZ bu bağlamı dizgeye çevirir;
    çalıştırma bağlamındaki aynı yazım hâlâ o sürümü İSTER. Ayrım bu yüzden şart.
    """
    kokler = []
    for d in ast.walk(agac):
        if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if d.returns is not None:
                kokler.append(d.returns)
            a = d.args
            gruplar = [getattr(a, "posonlyargs", None) or [], a.args, a.kwonlyargs]
            for grup in gruplar:
                for arg in grup:
                    if arg.annotation is not None:
                        kokler.append(arg.annotation)
            for arg in (a.vararg, a.kwarg):
                if arg is not None and arg.annotation is not None:
                    kokler.append(arg.annotation)
        elif isinstance(d, ast.AnnAssign) and d.annotation is not None:
            kokler.append(d.annotation)
    icinde = set()
    for k in kokler:
        for d in ast.walk(k):
            icinde.add(id(d))
    return icinde


def _tip_ifadesi_mi(d) -> bool:
    """`X | Y`nin operandı bir TİP gibi mi duruyor (yanlış-pozitif kesici)."""
    if isinstance(d, ast.Constant):
        return d.value is None
    if isinstance(d, ast.Name):
        return d.id in _TIP_ADLARI
    if isinstance(d, ast.Attribute):
        return d.attr in _TIP_ADLARI or d.attr[:1].isupper()
    if isinstance(d, ast.Subscript):
        return _pep585_mi(d) or _tip_ifadesi_mi(d.value)
    if isinstance(d, ast.BinOp) and isinstance(d.op, ast.BitOr):
        return _tip_ifadesi_mi(d.left) and _tip_ifadesi_mi(d.right)
    return False


def _pep585_mi(d) -> bool:
    return isinstance(d, ast.Subscript) and isinstance(d.value, ast.Name) \
        and d.value.id in _PEP585_ADLARI


def asgari_surum_turet(kaynak=None, yol=None):
    """KAYNAK METNİN gerçek asgari Python sürümünü TÜRETİR (literal YOK).

    Döner: (surum|None, kanit, sebep)
      * `surum is None` ⇒ `sebep` doludur ve hüküm FAIL-CLOSED'dur.
      * `kanit` = [(surum, etiket, satir), ...] — sayının NEREDEN geldiği.
    """
    yol = str(yol or BU_BETIK)
    if kaynak is None:
        try:
            with open(yol, encoding="utf-8") as f:
                kaynak = f.read()
        except Exception as e:
            return None, [], "KAYNAK_OKUNAMADI %s: %s" % (type(e).__name__, str(e)[:120])
    try:
        agac = ast.parse(kaynak, filename=yol)
    except SyntaxError as e:
        # 🔴 Bu KESİN OLUMSUZ bir hükümdür, "ölçemedim" değil: koşan yorumlayıcı
        #    bu kaynağı DERLEYEMİYOR. Sürüm numarası kıyaslamaya bile gerek yok.
        return None, [], "SOZDIZIM satir=%s: %s" % (
            getattr(e, "lineno", "-"), str(getattr(e, "msg", e))[:120])

    annot = _annotation_dugumleri(agac)
    kanit = []

    def talep(surum, etiket, dugum):
        kanit.append((surum, etiket, int(getattr(dugum, "lineno", 0) or 0)))

    gelecek_annot = False
    for d in ast.walk(agac):
        if isinstance(d, ast.ImportFrom) and d.module == "__future__":
            for al in d.names:
                if al.name == "annotations":
                    gelecek_annot = True
                    talep((3, 7), "from __future__ import annotations", d)

    Match = getattr(ast, "Match", None)
    TryStar = getattr(ast, "TryStar", None)
    NamedExpr = getattr(ast, "NamedExpr", None)

    for d in ast.walk(agac):
        annot_icinde = id(d) in annot
        if NamedExpr is not None and isinstance(d, NamedExpr):
            talep((3, 8), "walrus ':='", d)
        elif isinstance(d, ast.arguments) and getattr(d, "posonlyargs", None):
            talep((3, 8), "yalniz-konumsal parametre '/'", d)
        elif Match is not None and isinstance(d, Match):
            talep((3, 10), "match/case", d)
        elif TryStar is not None and isinstance(d, TryStar):
            talep((3, 11), "except*", d)
        elif isinstance(d, ast.BinOp) and isinstance(d.op, ast.BitOr) \
                and _tip_ifadesi_mi(d.left) and _tip_ifadesi_mi(d.right):
            if annot_icinde and gelecek_annot:
                continue  # dizgeye döner; çalıştırma anında DEĞERLENDİRİLMEZ
            talep((3, 10), "PEP604 'X | Y'%s" % (
                " (annotation, __future__ YOK)" if annot_icinde else " (calistirma baglami)"), d)
        elif _pep585_mi(d):
            if annot_icinde and gelecek_annot:
                continue
            talep((3, 9), "PEP585 '%s[...]'%s" % (
                d.value.id,
                " (annotation, __future__ YOK)" if annot_icinde else " (calistirma baglami)"), d)

    if not kanit:
        return _SURUM_TABANI, [], ""
    return max(k[0] for k in kanit), kanit, ""


# 🔴 TÜRETİLİR — modül yüklenirken, KENDİ kaynağından. Elle atanmaz.
ASGARI_SURUM, ASGARI_KANIT, ASGARI_SEBEP = asgari_surum_turet()


def asgari_dizgesi(surum=-1) -> str:
    """(3, 10) -> '3.10' · None -> 'OLCULEMEDI'. Varsayılan: bu betiğinki."""
    if surum == -1:
        surum = ASGARI_SURUM
    if surum is None:
        return "OLCULEMEDI"
    return "%d.%d" % (surum[0], surum[1])


def asgari_kaynagi() -> str:
    """Sayının NEREDEN türediği — tek satır, makine-okunur."""
    if ASGARI_SEBEP:
        return ASGARI_SEBEP.replace(" ", "_")
    if not ASGARI_KANIT:
        return "TABAN_%d.%d(surum-kapili_sozdizimi_YOK)" % _SURUM_TABANI
    en = max(k[0] for k in ASGARI_KANIT)
    etiket, satir = [(k[1], k[2]) for k in ASGARI_KANIT if k[0] == en][0]
    return "%s@satir%d" % (etiket.replace(" ", "_"), satir)


def ortam_satiri() -> str:
    """Koşum ortamının TEK SATIRLIK, makine-okunur raporu."""
    uyum = "EVET" if ortam_uyumlu() else "HAYIR"
    return "ORTAM yorumlayici=%s surum=%s ASGARI=%s ASGARI_KAYNAK=%s UYUM=%s" % (
        sys.executable or "-", surum_dizgesi(), asgari_dizgesi(), asgari_kaynagi(), uyum)


def ortam_uyumlu() -> bool:
    # 🔴 FAIL-CLOSED: türetilemediyse UYUMLU SAYILMAZ.
    if ASGARI_SURUM is None:
        return False
    return sys.version_info[:2] >= ASGARI_SURUM


def crontab_yorumlayicilari(betik=None, crontab_metni=None):
    """crontab'ta BU betiği çağıran satırların YORUMLAYICILARI.

    🔴 İKİZ TANIM YOK: yorumlayıcı adı buraya ELLE yazılmaz, kendi kaynağından
    (`crontab -l`) okunur. Crontab yarın `/opt/homebrew/bin/python3`e çevrilse
    kabul kolu kendiliğinden ONU ölçer.

    Döner: (yorumlayicilar, sebep). Liste BOŞ ve sebep dolu ise ÖLÇÜLEMEDİ.
    """
    betik = str(betik or BU_BETIK)
    hedef_ad = os.path.basename(betik)
    if crontab_metni is None:
        try:
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=20)
        except FileNotFoundError:
            return [], "crontab PATH'ta yok"
        except subprocess.TimeoutExpired:
            return [], "crontab timeout 20s"
        except Exception as e:
            return [], "%s: %s" % (type(e).__name__, str(e)[:100])
        if r.returncode != 0:
            return [], "crontab -l rc=%d" % r.returncode
        crontab_metni = r.stdout or ""

    bulunan = []
    for satir in crontab_metni.splitlines():
        s = satir.strip()
        if not s or s.startswith("#"):
            continue
        if hedef_ad not in s:
            continue
        parcalar = s.split()
        for i, p in enumerate(parcalar):
            if p.endswith(hedef_ad) and i > 0:
                aday = parcalar[i - 1]
                if "python" in os.path.basename(aday):
                    bulunan.append(aday)
                break
    if not bulunan:
        return [], "crontab'ta %s satiri YOK" % hedef_ad
    # benzersiz + sıralı
    return sorted(set(bulunan)), ""


def capraz_ortam_olc(betik=None, crontab_metni=None):
    """② VARSAYIM ÖLÇÜMÜ: crontab'ın NAMED yorumlayıcısı bu aracı FİİLEN
    çalıştırabiliyor mu. Sadece sürüm KIYASLAMAZ — aracı gerçekten koşturur,
    çünkü bugünkü arıza bir SÜRÜM numarası değil, bir ÇALIŞTIRMA hatasıydı.

    Döner: (hukum, satirlar). hukum ∈ {GECTI, DUSTU, OLCULEMEDI}
    """
    betik = str(betik or BU_BETIK)
    yorumlayicilar, sebep = crontab_yorumlayicilari(betik, crontab_metni)
    if not yorumlayicilar:
        return "OLCULEMEDI", ["CAPRAZ_ORTAM=OLCULEMEDI sebep=%s" % (sebep or "-")]

    satirlar = []
    dusen = 0
    for py in yorumlayicilar:
        if not os.path.exists(py):
            satirlar.append("CAPRAZ_ORTAM yorumlayici=%s SONUC=YOK (diskte bulunamadi)" % py)
            dusen += 1
            continue
        try:
            r = subprocess.run([py, betik, "--ortam-testi"],
                               capture_output=True, text=True, timeout=60)
            rc = r.returncode
            son = (r.stdout or "").strip().splitlines()
            son = son[-1] if son else ((r.stderr or "").strip().splitlines() or ["-"])[-1]
        except Exception as e:
            rc, son = 125, "%s: %s" % (type(e).__name__, str(e)[:120])
        satirlar.append("CAPRAZ_ORTAM yorumlayici=%s rc=%d SONUC=%s | %s" % (
            py, rc, "GECTI" if rc == 0 else "DUSTU", son[:160]))
        if rc != 0:
            dusen += 1
    satirlar.append("CAPRAZ_ORTAM_OZET adet=%d dusen=%d" % (len(yorumlayicilar), dusen))
    return ("GECTI" if dusen == 0 else "DUSTU"), satirlar


def oku_yol(p: Path) -> str | None:
    """Salt okuma; yoksa/okunamazsa None döner (fail-loud kanalı)."""
    try:
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def acik_kalemleri_topla(kalemler_txt: str) -> tuple[list[dict], int]:
    """Markdown tablo satırlarını parse eder; durum ACIK veya 🔧 olanları döner.
    Tablo formatı: '| id | tarih | kimden→kime | iş | durum | kapanış kanıtı |'.
    'iş' hücresi içinde '|' veya '\n' olabilir (uzun metin). Bu yüzden:
      - İlk 3 hücre (id/tarih/kimden) sabit konumda (F0,F1,F2).
      - Son 2 hücre (durum/kanit) sabit konumda (F-2,F-1).
      - Aradaki TÜM hücreler 'iş' hücresine toplanır.
    Boş dönerse (>=0) çağıran "ölçülemedi" dememeli; None ise zaten okunamadı demektir.
    """
    out: list[dict] = []
    if kalemler_txt is None:
        return out, 0
    id_re = re.compile(r"^\|\s*(K\d+)\s*\|")
    for line in kalemler_txt.splitlines():
        m_id = id_re.match(line)
        if not m_id:
            continue
        # "| Kxx | a | b | c | d | e |" → split " | " → ["| Kxx", "a", "b", "c", "d", "e", ""]
        # sondaki "" kalan "|"; başta "| Kxx" id'yi taşır
        parts = line.rstrip().rstrip("|").split(" | ")
        if len(parts) < 4:
            continue
        # id F0 başından "| " sıyır
        kid = parts[0].lstrip("| ").strip()
        tarih = parts[1].strip() if len(parts) > 1 else ""
        kimden = parts[2].strip() if len(parts) > 2 else ""
        durum = parts[-2].strip() if len(parts) >= 2 else ""
        kanit = parts[-1].strip() if len(parts) >= 1 else ""
        # 'iş' hücresi F3..F-3 (yoksa F3)
        is_hucreleri = parts[3:-2] if len(parts) > 5 else ([parts[3]] if len(parts) > 3 else [])
        is_metni = " | ".join(is_hucreleri).strip()
        if durum in ("ACIK", "🔧"):
            out.append({
                "id": kid,
                "tarih": tarih,
                "kimden": kimden,
                "is": is_metni[:200],
                "durum": durum,
                "kanit": kanit[:120],
            })
    return out, len(out)


def bugunun_kirmizilari() -> tuple[str, int]:
    """gh run list bugünün kırmızılarını döner. gh yoksa/başarısızsa ('CI=OLCULEMEDI', 0).
    Dönüş: (metin_blok, adet)."""
    try:
        r = subprocess.run(
            ["gh", "run", "list", "--limit", "30", "--json", "conclusion,name,createdAt,headBranch"],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return "CI=OLCULEMEDI (gh run list rc={})\n{}".format(r.returncode, r.stderr.strip()[:200]), 0
        import json
        data = json.loads(r.stdout or "[]")
        bugun = dt.datetime.now(dt.timezone.utc).date()
        kirmizi = []
        for run in data:
            conc = (run.get("conclusion") or "").lower()
            if conc not in ("failure", "cancelled", "timed_out"):
                continue
            ts = run.get("createdAt", "")
            try:
                run_date = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
            except Exception:
                continue
            if run_date != bugun:
                continue
            kirmizi.append("- [{}] {} · dal={}".format(conc, run.get("name", "?"), run.get("headBranch", "?")))
        if not kirmizi:
            return "Bugün kırmızı CI yok (ölçülen 30 koşumun filtresi: sadece bugün + failure/cancelled/timed_out).", 0
        return "\n".join(kirmizi), len(kirmizi)
    except FileNotFoundError:
        return "CI=OLCULEMEDI (gh PATH'ta yok)", 0
    except subprocess.TimeoutExpired:
        return "CI=OLCULEMEDI (gh timeout 20s)", 0
    except Exception as e:
        return "CI=OLCULEMEDI ({}: {})".format(type(e).__name__, str(e)[:120]), 0


def merge_kuyrugu() -> tuple[str, int]:
    """main dışı dalları listeler; merge bekleyenleri ölçer.
    Dönüş: (metin_blok, adet)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO), "branch", "-a"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return "DAL=OLCULEMEDI (git branch rc={})".format(r.returncode), 0
        dallar = []
        for line in (r.stdout or "").splitlines():
            s = line.strip().lstrip("*").strip()
            if not s or s.startswith("remotes/origin/HEAD"):
                continue
            # 'main' ya da 'origin/main' YOK sayılır; çıplak '*' olmayanlar da uzak
            if s == "main" or s == "origin/main" or s.endswith("/main") or s.endswith("/HEAD"):
                continue
            # Uzaktaki origin/<x> ve yerel <x> ayrımı; origin/ prefix'i sıyır
            temiz = s.replace("remotes/origin/", "")
            dallar.append(temiz)
        # benzersiz + sıralı
        dallar = sorted(set(dallar))
        if not dallar:
            return "Main dışı dal YOK (yalnız main var).", 0
        satirlar = ["- " + d for d in dallar]
        # kapsam ölçmek pahalı (her dal için merge-base + diff); burada YALNIZCA dal adedi raporlanır
        satirlar.append("")
        satirlar.append("> Kapsam ölçümü (merge-base + diff --stat) HER DAL İÇİN ayrı koşulur; bu özet yalnız adı verir, boyut chip düşünce hesaplanır.")
        return "\n".join(satirlar), len(dallar)
    except subprocess.TimeoutExpired:
        return "DAL=OLCULEMEDI (git branch timeout)", 0
    except Exception as e:
        return "DAL=OLCULEMEDI ({}: {})".format(type(e).__name__, str(e)[:120]), 0


def kutuda_yeni(kutu_txt: str | None) -> tuple[str, int]:
    """Son 24 saatte kutuya düşen '## YYYY-MM-DD — ...' başlıklarını sayar.
    Bugünün tarihini TÜRKİYE saatine göre alır (yerel makine)."""
    if kutu_txt is None:
        return "KUTU=OLCULEMEDI (kutu okunamadı)", 0
    bugun = dt.date.today()
    dun = bugun - dt.timedelta(days=1)
    baslik_re = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*[—-]")
    bulunan: list[str] = []
    for line in kutu_txt.splitlines():
        m = baslik_re.match(line)
        if not m:
            continue
        tarih = dt.date.fromisoformat(m.group(1))
        if tarih in (bugun, dun):
            bulunan.append(line.strip())
    if not bulunan:
        return "Son 24 saatte kutuya yeni blok DÜŞMEMİŞ ({} ve {} boş).".format(dun, bugun), 0
    satirlar = ["- " + b for b in bulunan]
    satirlar.append("")
    satirlar.append("> Tam metin kutu dosyasında; bu yalnız başlık indeksidir.")
    return "\n".join(satirlar), len(bulunan)


def devam_ozet(devam_txt: str | None) -> str:
    """DEVAM.md'nin üstündeki canlı bloktan kısa özet (ilk 40 satır)."""
    if devam_txt is None:
        return "DEVAM=OLCULEMEDI"
    satirlar = devam_txt.splitlines()[:40]
    return "\n".join(satirlar)


def spec_yaz(icerik: str, tarih: dt.date, kuru: bool, spec_dizin=None):
    """Hedef yolu hesaplar; kuru=False ise yazar, True ise yazmaz (yolu döner).

    🔴 27 Ağu: yazım artık İSTİSNA FIRLATMAZ. Eskiden `write_text` bir OSError
    verirse araç traceback ile ölürdü ve SONUÇ KOLU hiç koşamazdı — yani asıl
    ölçmek istediğimiz hâl (spec üretilmedi) ölçüm kolunu da öldürüyordu.
    Döner: (hedef_yol, hata_dizgesi|None)
    """
    dizin = Path(spec_dizin) if spec_dizin else SPEC_DIR
    hedef = dizin / "KraL-Tamirci-{}.md".format(tarih.strftime("%Y%m%d"))
    if kuru:
        return hedef, None
    try:
        dizin.mkdir(parents=True, exist_ok=True)
        hedef.write_text(icerik, encoding="utf-8")
    except Exception as e:
        return hedef, "%s: %s" % (type(e).__name__, str(e)[:120])
    return hedef, None


def sonuc_kolu(hedef, kuru: bool, yazim_hatasi=None) -> tuple[str, bool]:
    """③ SONUÇ KOLU — "spec ÜRETİLDİ Mİ" sorusunu SORAN tek yer.

    🔴 Bu kol `rc`'ye BAKMAZ; DİSKE bakar. Bugünkü arızanın gizlenme biçimi tam
    olarak buydu: hiçbir kol sonucu ölçmüyordu. `rc=0` dönen bir koşumda bile
    dosya yoksa bu bir ARIZADIR ve ADIYLA raporlanır.

    Döner: (satir, kirmizi_mi)
    """
    if kuru:
        return "SONUC_KOLU=KURU yol=%s (yazim istenmedi)" % hedef, False
    if yazim_hatasi:
        return ("SONUC_KOLU=SPEC_URETILMEDI yol=%s boyut=-1 sebep=YAZILAMADI:%s"
                % (hedef, yazim_hatasi)), True
    try:
        if not os.path.isfile(str(hedef)):
            return ("SONUC_KOLU=SPEC_URETILMEDI yol=%s boyut=-1 sebep=DOSYA_YOK"
                    % hedef), True
        boyut = os.path.getsize(str(hedef))
    except OSError as e:
        return ("SONUC_KOLU=SPEC_URETILMEDI yol=%s boyut=-1 sebep=OLCULEMEDI:%s"
                % (hedef, type(e).__name__)), True
    if boyut <= 0:
        return ("SONUC_KOLU=SPEC_URETILMEDI yol=%s boyut=%d sebep=BOS_DOSYA"
                % (hedef, boyut)), True
    return "SONUC_KOLU=SPEC_VAR yol=%s boyut=%d" % (hedef, boyut), False


def build_spec(tarih: dt.date, kalemler: list[dict], kirmizi_blok: str, dal_blok: str,
               kutu_blok: str, devam_blok: str, kirmizi_n: int, dal_n: int, kutu_n: int,
               okunabilir: dict) -> str:
    """Spec gövdesini kurar. ZORUNLU bölümler: KIRMIZI · MERGE · KALEMLER · KUTUDA YENİ · DİSİPLİN."""
    baslik = "# KraL-Tamirci-{} — sabah spec'i\n".format(tarih.isoformat())
    meta = (
        "Ev: KraL · Etiket: `kabul-sabah-rutini` · Üretici: `/Users/okan/.claude/cron/kral-sabah.py`\n"
        "Üretim anı: {} (yerel TR) · MANDATE: o günün Tamirci çipinin TEK spec'idir.\n".format(
            dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    kalem_blok = ""
    if not kalemler and not okunabilir["kalemler"]:
        kalem_blok = "ACIK KALEMLER=OLCULEMEDI (acik-kalemler.md okunamadı)"
    elif not kalemler:
        kalem_blok = "ACIK KALEM=YOK (defter boş, hepsi KAPANDI)."
    else:
        satirlar = []
        for k in kalemler:
            satirlar.append(
                "- **{id}** [{durum}] {is_}  \n  _kimden:_ {kimden} · _kanıt sütunu:_ {kanit}".format(
                    id=k["id"], durum=k["durum"], is_=k["is"], kimden=k["kimden"], kanit=k["kanit"]
                )
            )
        kalem_blok = "\n".join(satirlar)

    disiplin = (
        "## DİSİPLİN\n"
        "- Rapor, işçi→mimar rapor protokol adıyla yazılır ve DALDA tutulur; İZLENEN bırakılamaz.\n"
        "- İşçi etiketi `kabul-` içerir; `kabul:` alanı doluysa kalem kapatılabilir.\n"
        "- Bu rutin İŞÇİ DAĞITMAZ / TUR AÇMAZ — yalnız spec üretir; çipi teslim kolu düşürür.\n"
        "- Ölçülemeyen alana `OLCULEMEDI` yazılır; SESSİZCE sıfır yazılmaz.\n"
        "- Dosya yolu: `~/.claude/cron/tamirci-spec/` (git-dışı; diske yazılır, repoya GİRMEZ).\n"
    )

    giris_durumu = (
        "## GİRİŞ DURUMU (okunabilirlik)\n"
        "- kutu: {kutu}\n"
        "- acik-kalemler.md: {kalemler}\n"
        "- DEVAM.md: {devam}\n"
        "- gh run list: {gh}\n"
        "- git branch: {git}\n".format(
            kutu="OK" if okunabilir["kutu"] else "OLCULEMEDI",
            kalemler="OK" if okunabilir["kalemler"] else "OLCULEMEDI",
            devam="OK" if okunabilir["devam"] else "OLCULEMEDI",
            gh="OK" if okunabilir["gh"] else "OLCULEMEDI",
            git="OK" if okunabilir["git"] else "OLCULEMEDI",
        )
    )

    return "\n".join([
        baslik, meta,
        "## BUGÜNÜN KIRMIZILARI (CI — bugün UTC)\n" + kirmizi_blok + "\n",
        "## MERGE KUYRUĞU (main dışı dallar)\n" + dal_blok + "\n",
        "## AÇIK KALEMLER (defter — `acik-kalemler.md`, durum ∈ {ACIK, 🔧})\n" + kalem_blok + "\n",
        "## KUTUDA YENİ (son 24 saat — bugün+dün)\n" + kutu_blok + "\n",
        "## DEVAM (canlı — ilk 40 satır özeti)\n```\n" + devam_blok + "\n```\n",
        disiplin,
        giris_durumu,
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description="KraL sabah spec'i")
    ap.add_argument("--kuru", action="store_true", help="dosya yazma, yalnız özet bas")
    ap.add_argument("--kendini-test", action="store_true", help="iç sağlık + çapraz ortam (A1)")
    ap.add_argument("--ortam-testi", action="store_true",
                    help="modülü yükler, tek satır ortam raporu basar (çapraz ölçüm hedefi)")
    ap.add_argument("--spec-dizin", default=None,
                    help="spec'in yazılacağı dizin (A3 fikstürü; varsayılan ~/.claude/cron/tamirci-spec)")
    ap.add_argument("--asgari", nargs="?", const="", default=None, metavar="YOL",
                    help="verilen dosyanın (varsayılan: bu betik) asgari sürümünü TÜRETİP basar")
    args = ap.parse_args()

    # --- --asgari: türetme kolunun FİKSTÜRE UYGULANABİLİR yüzü. Bir 3.10
    #     yorumlayıcısı olmadan da "bu kaynak 3.10 ister" hükmü ölçülebilsin
    #     diye ayrı bayrak; ORTAM kolundan ÖNCE, çünkü uyumsuz kaynağı da
    #     ölçebilmeli. ---
    if args.asgari is not None:
        hedef = args.asgari or str(BU_BETIK)
        surum, kanit, sebep = asgari_surum_turet(yol=hedef)
        uyum = "HAYIR" if surum is None else (
            "EVET" if sys.version_info[:2] >= surum else "HAYIR")
        en = None if surum is None else max(k[0] for k in kanit) if kanit else surum
        if sebep:
            kaynak_alani = sebep.replace(" ", "_")
        elif not kanit:
            kaynak_alani = "TABAN_%d.%d(surum-kapili_sozdizimi_YOK)" % _SURUM_TABANI
        else:
            etiket, satir = [(k[1], k[2]) for k in kanit if k[0] == en][0]
            kaynak_alani = "%s@satir%d" % (etiket.replace(" ", "_"), satir)
        print("ASGARI_TURETME hedef=%s ASGARI=%s ASGARI_KAYNAK=%s kanit=%d UYUM=%s" % (
            hedef, asgari_dizgesi(surum), kaynak_alani, len(kanit), uyum))
        for s, etiket, satir in sorted(kanit, reverse=True):
            print("  KANIT %d.%d  %-52s satir=%d" % (s[0], s[1], etiket, satir))
        return 0 if uyum == "EVET" else 3

    # --- ① ORTAM: her koşumun İLK satırı; uyumsuzluk ADIYLA basılır ---
    print(ortam_satiri())
    if not ortam_uyumlu():
        print("ORTAM_UYUMSUZ: bu araç en az Python %s ister, koşum %s ile yapıldı "
              "(kaynak: %s). SESSIZ COKME YERINE ADIYLA DURDUM." % (
                  asgari_dizgesi(), surum_dizgesi(), asgari_kaynagi()), file=sys.stderr)
        return 3

    # --- --ortam-testi: çapraz ölçümün HEDEFİ. Modül YÜKLENDİ (annotation'lar
    #     dahil), argparse koştu; bugünkü arıza bu noktaya gelmeden düşerdi. ---
    if args.ortam_testi:
        print("ORTAM_TESTI=OK")
        return 0

    # --- girdi okuma (fail-loud) ---
    kutu_txt = oku_yol(KUTU)
    kalem_txt = oku_yol(KALEMLER)
    devam_txt = oku_yol(DEVAM)
    okunabilir = {"kutu": kutu_txt is not None, "kalemler": kalem_txt is not None,
                  "devam": devam_txt is not None}

    # --- toplama ---
    kalemler, kalem_n = acik_kalemleri_topla(kalem_txt)
    kirmizi_blok, kirmizi_n = bugunun_kirmizilari()
    dal_blok, dal_n = merge_kuyrugu()
    kutu_blok, kutu_n = kutuda_yeni(kutu_txt)
    devam_blok = devam_ozet(devam_txt)

    okunabilir["gh"] = not kirmizi_blok.startswith("CI=OLCULEMEDI")
    okunabilir["git"] = not dal_blok.startswith("DAL=OLCULEMEDI")

    # --- spec inşası ---
    bugun = dt.date.today()
    spec = build_spec(bugun, kalemler, kirmizi_blok, dal_blok, kutu_blok, devam_blok,
                      kirmizi_n, dal_n, kutu_n, okunabilir)

    # --- fail-loud: KALEMLER okunamadıysa ---
    rc = 0
    if not okunabilir["kalemler"]:
        rc = 1

    # --- yazma ---
    # `--kendini-test` YAZMAZ (27 Ağu): sağlık kontrolünün yan etkisi günün
    # kanıtını üretmek olmamalı — aksi halde A2 ("gerçek koşum spec üretiyor")
    # kabulü kendi test koşumuyla YEŞİLE boyanırdı.
    kuru = bool(args.kuru or args.kendini_test)
    hedef, yazim_hatasi = spec_yaz(spec, bugun, kuru=kuru, spec_dizin=args.spec_dizin)
    sabah_spec_alan = "KURU" if kuru else str(hedef)

    # --- çıktı: tek özet satırı ---
    print("SABAH_SPEC={} KALEM={} KIRMIZI={} DAL={} KUTU_YENI={} rc={}".format(
        sabah_spec_alan, kalem_n, kirmizi_n, dal_n, kutu_n, rc
    ))

    # --- ③ SONUÇ KOLU: rc'den BAĞIMSIZ, diskten ölçer ---
    sonuc_satiri, sonuc_kirmizi = sonuc_kolu(hedef, kuru, yazim_hatasi)
    print(sonuc_satiri)
    if sonuc_kirmizi:
        rc = max(rc, 1)

    # --- ② kendini-test: ÇAPRAZ ORTAM ÖLÇÜMÜ + iç sağlık ---
    if args.kendini_test:
        ek = []
        ek.append("KENDINI_TEST: KUTU={} KALEMLER={} DEVAM={} GH={} GIT={}".format(
            "OK" if okunabilir["kutu"] else "OLCULEMEDI",
            "OK" if okunabilir["kalemler"] else "OLCULEMEDI",
            "OK" if okunabilir["devam"] else "OLCULEMEDI",
            "OK" if okunabilir["gh"] else "OLCULEMEDI",
            "OK" if okunabilir["git"] else "OLCULEMEDI",
        ))
        ek.append("KENDINI_TEST: KALEM_ADET_OKUMA={}".format("VAR" if kalem_txt is not None else "YOK"))
        ek.append("KENDINI_TEST: SPEC_BASLIK='# KraL-Tamirci-{}'".format(bugun.isoformat()))
        ek.append("KENDINI_TEST: SPEC_UZUNLUK={}".format(len(spec)))
        print("\n".join(ek))

        hukum, satirlar = capraz_ortam_olc()
        print("\n".join(satirlar))
        print("KENDINI_TEST: CAPRAZ_ORTAM=%s" % hukum)
        if hukum != "GECTI":
            rc = max(rc, 1)
        return rc

    return rc


if __name__ == "__main__":
    sys.exit(main())
