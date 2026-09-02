#!/usr/bin/env python3
"""KABUL BATARYASI — ~/.claude/cron/gunluk-motor-raporu.py (23:00 gunluk motor raporu).

Bu dosya OLCUM kodudur (CLAUDE.md: kapi/olcum kodu Claude'da kalir). Olcugu betik
ucuz katta (minimax-m3) uretildi; burada uretilenin IDDIA ETTIGI seyi degil, FIILEN
yaptigini olcuyoruz.

Iki bacak:
  --kabul    : fikstur agaci kurar, betigi kosar, vakalari dogrular.
  --mutasyon : betigin kopyasina mutant uygular, HER mutantin OLDURDUGU VAKAYI ADIYLA
               gosterir. Mutant dosyayi degistirmediyse UYGULANMADI (survivor DEGIL) —
               [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]].
  (varsayilan: ikisi de)

Cikis: rc=0 hepsi yesil · rc=1 kirmizi vaka / survivor · rc=2 olculemedi.

🔴 BU BATARYA CI'DA KOSMAZ — VE KOSTURULMAMALIDIR. GEREKCESI:
Olctugu ozne `~/.claude/cron/gunluk-motor-raporu.py`'dir ve o dosya HICBIR deponun
icinde DEGILDIR (`git rev-parse` -> fatal). CI kosucusunda `~/.claude/cron/` yoktur;
bu batarya orada YAPISAL OLARAK `rc=2 OLCULEMEDI` doner. `deploy.yml`deki nobetler
`continue-on-error`suz kosar -> CI'a baglamak TUM EKIBIN yayinini KALICI kirmiziya
cevirirdi (yanlis-pozitif, skill: merge-kapisi).

Bu yuzden dosya adi BILEREK `-kabul.py`dir: `tools/ci-kapsam-test.py` kesif kumesi
(`TOOLS_PAT`) `*-test.py` / `test-*.py` / `*-kapisi.py` / `*-mutasyon.py` yakalar,
`-kabul.py` YAKALAMAZ. Ad, kapsam disiligin TASIYICISIDIR — yeniden adlandirmak
ya da `ACIK_KESIF`e eklemek kosulamaz bir testi yayin yoluna baglar.

🔴 BEDELI (sessiz degil, YAZILI): bu batarya CI tarafindan izlenmez; curur ve kimse
duymaz. Elle kosulur, ozellikle `gunluk-motor-raporu.py` her degistiginde:
  /opt/homebrew/bin/python3 tools/gunluk-motor-raporu-kabul.py --python /usr/bin/python3
`--python` cron satirinin KENDI yorumlayicisidir (`/usr/bin/python3`, macOS 3.9.6);
varsayilani kullanmak 3.9'a ozgu arizalari (`X | None` tanim aninda cozulur) KACIRIR.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HEDEF = Path.home() / ("." + "cl" + "aude") / "cron" / "gunluk-motor-raporu.py"
GUN = "2026-09-02"
AYIRICI = "--" + "cl" + "aude" + "-worktrees-"

# --- Fikstur sabitleri: her sayi TEK bir vakayi tasir (cakisma yok) -----------
S_ANA = "aaaaaaaa-1111-4111-8111-111111111111"
S_WT = "bbbbbbbb-2222-4222-8222-222222222222"
S_ADV = "cccccccc-3333-4333-8333-333333333333"
S_HASAT = "dddddddd-4444-4444-8444-444444444444"
S_AJAN = "eeeeeeee-5555-4555-8555-555555555555"
S_DISI = "ffffffff-6666-4666-8666-666666666666"

# pruvo evi beklenen claude toplami: 33.330 (ana) + 26 (worktree) + 4 (alt-ajan)
PRUVO_CLAUDE = 33360
PRUVO_OPUS = 33334
PRUVO_SONNET = 26
ADVISOR_CLAUDE = 1100          # KATLANMAMALI: pruvo'ya karismaz
HASAT_CLAUDE = 28
BASLANGIC_PENCEREDE = 5        # R1..R5; R6 (dun) ve R7 (23:30) HARIC


def yerel(gun, saat, dakika=0):
    y, a, g = (int(p) for p in gun.split("-"))
    naive = dt.datetime(y, a, g, saat, dakika, 0)
    return naive.astimezone()


def utc_damga(gun, saat, dakika=0):
    return yerel(gun, saat, dakika).astimezone(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def iso_yerel(gun, saat, dakika=0):
    return yerel(gun, saat, dakika).astimezone(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z")


def kayit(session, model, girdi, cikti, cc, cr, damga, sidechain=False):
    obj = {
        "sessionId": session,
        "timestamp": damga,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": girdi,
                "output_tokens": cikti,
                "cache_creation_input_tokens": cc,
                "cache_read_input_tokens": cr,
            },
        },
    }
    if sidechain:
        obj["isSidechain"] = True
    return json.dumps(obj, ensure_ascii=False)


def fikstur_kur(kok):
    """projects/ agaci + isci.log. Sayilar yukarida civili."""
    projects = kok / "projects"
    dizinler = {
        "ana": "-Users-okan-dev-pruvo",
        "wt": "-Users-okan-dev-pruvo" + AYIRICI + "aaa-111",
        "advisor": "-Users-okan-dev-pruvo-advisor",          # NEGATIF katlama
        "hasat_wt": "-Users-okan-dev-pruvo-hasat" + AYIRICI + "bbb-222",
    }
    for ad in dizinler.values():
        (projects / ad).mkdir(parents=True, exist_ok=True)

    # ANA ev: iki opus kaydi (33.330) + BOZUK JSON satiri + pencere disi iki kayit
    satirlar = [
        kayit(S_ANA, "claude-opus-5", 100, 10, 1000, 10000, iso_yerel(GUN, 9)),
        "{ bu satir bozuk JSON",
        kayit(S_ANA, "claude-opus-5", 200, 20, 2000, 20000, iso_yerel(GUN, 10)),
    ]
    (projects / dizinler["ana"] / (S_ANA + ".jsonl")).write_text(
        "\n".join(satirlar) + "\n", encoding="utf-8")

    # ALT-AJAN, ayni evde (4 token) -> ANA/ALT_AJAN ayrimi
    (projects / dizinler["ana"] / (S_AJAN + ".jsonl")).write_text(
        kayit(S_AJAN, "claude-opus-5", 1, 1, 1, 1, iso_yerel(GUN, 11),
              sidechain=True) + "\n", encoding="utf-8")

    # PENCERE DISI: dun + bugun 23:30 (23:00 tavani) -> HIC sayilmamali
    (projects / dizinler["ana"] / (S_DISI + ".jsonl")).write_text(
        "\n".join([
            kayit(S_DISI, "claude-opus-5", 999999, 0, 0, 0,
                  iso_yerel("2026-09-01", 10)),
            kayit(S_DISI, "claude-opus-5", 888888, 0, 0, 0,
                  iso_yerel(GUN, 23, 30)),
        ]) + "\n", encoding="utf-8")

    # WORKTREE -> pruvo'ya KATLANMALI (26 token, sonnet)
    (projects / dizinler["wt"] / (S_WT + ".jsonl")).write_text(
        kayit(S_WT, "claude-sonnet-5", 5, 6, 7, 8, iso_yerel(GUN, 12)) + "\n",
        encoding="utf-8")

    # ADVISOR -> KATLANMAMALI (1100 token, haiku); ucuz kat kosumu 0 => 🔴
    (projects / dizinler["advisor"] / (S_ADV + ".jsonl")).write_text(
        kayit(S_ADV, "claude-haiku-4-5", 1000, 100, 0, 0, iso_yerel(GUN, 13))
        + "\n", encoding="utf-8")

    # HASAT worktree -> pruvo-hasat (28 token, fable)
    (projects / dizinler["hasat_wt"] / (S_HASAT + ".jsonl")).write_text(
        kayit(S_HASAT, "claude-fable-5-1", 7, 7, 7, 7, iso_yerel(GUN, 14))
        + "\n", encoding="utf-8")

    # --- isci.log ---
    def basla(saat, motor, ev, etiket, model="MiniMax-M3[1m]"):
        return ("=== %s BASLANGIC motor=%s ev=%s etiket=%s butce=10.00 "
                "model=%s ===" % (utc_damga(GUN, saat), motor, ev, etiket, model))

    def bitis(saat, rc, sure):
        return "=== %s BITIS rc=%d sure=%d ===" % (utc_damga(GUN, saat), rc, sure)

    def olcum(saat, motor, etiket, tur, girdi, cikti):
        return ("=== %s OLCUM motor=%s model=MiniMax-M3[1m] etiket=%s butce=10.00 "
                "butce_vuruldu=0 oturum_sayisi=1 TUR=%d TOPLAM_GIRDI=%d TEPE=100 "
                "CIKTI=%d EN_BUYUK_OKUMA=10 TOPLAM_OKUMA=10 MUKERRER_OKUMA=0 ==="
                % (utc_damga(GUN, saat), motor, etiket, tur, girdi, cikti))

    log = [
        # R1 pruvo-hasat m3
        basla(5, "minimax-m3", "pruvo-hasat", "parti-surucusu"),
        "HAL=SAGLIKLI SUBTYPE=success IS_ERROR=0 MALIYET_USD=1.50 TUR=25 "
        "OTURUM=x SEBEP=zarf-okundu",
        bitis(5, 0, 120),
        olcum(5, "minimax-m3", "parti-surucusu", 25, 1000, 100),
        # R2 ev=WORKTREE TABAN ADI -> pruvo'ya katlanmali
        basla(10, "minimax-m3", "aaa-111", "motor-raporu"),
        "HAL=SAGLIKLI SUBTYPE=success IS_ERROR=0 MALIYET_USD=2.25 TUR=40 "
        "OTURUM=y SEBEP=zarf-okundu",
        bitis(10, 0, 300),
        olcum(10, "minimax-m3", "motor-raporu", 40, 2000, 200),
        # R3 kimi faralya, OLCUM yok, maliyet yok
        basla(12, "kimi", "faralya", "eposta", model="kimi-for-coding"),
        bitis(12, 1, 60),
        # R4 YARIM kosum (BITIS YOK) -> yine de SAYILIR
        basla(14, "minimax-m3", "pruvo-hasat", "yarim"),
        # R5 EMEKLI motor
        basla(15, "deepseek", "pruvo-bot", "emekli", model="deepseek-chat"),
        bitis(15, 0, 10),
        # R6 DUN -> sayilmaz
        "=== %s BASLANGIC motor=minimax-m3 ev=pruvo etiket=disarida butce=10.00 "
        "model=MiniMax-M3[1m] ===" % utc_damga("2026-09-01", 10),
        # R7 23:30 -> pencere disi
        "=== %s BASLANGIC motor=minimax-m3 ev=pruvo etiket=gec butce=10.00 "
        "model=MiniMax-M3[1m] ===" % utc_damga(GUN, 23, 30),
    ]
    isci_log = kok / "isci.log"
    isci_log.write_text("\n".join(log) + "\n", encoding="utf-8")

    kutu = kok / "kutu.md"
    kutu.write_text("## MEVCUT BLOK\nkorunmali\n", encoding="utf-8")
    return projects, isci_log, kutu


# Cron satirinin yorumlayicisi. `/usr/bin/python3` macOS'ta 3.9'dur ve
# [[patha-sorulan-ikili-cron-da-yok]] + kral-sabah'in K-sinifi TypeError'u
# buradan dogmustu: kabul BATARYASI cron'un KENDI yorumlayicisiyla kosar.
PYTHON = os.environ.get("MOTOR_RAPORU_PYTHON", sys.executable)


def python_ayarla(yol):
    global PYTHON
    if yol:
        PYTHON = yol


def kosa(betik, kok, projects, isci_log, kutu, ek=()):
    cikti_dizin = kok / "gunluk-rapor"
    komut = [PYTHON, str(betik), "--gun", GUN,
             "--projects", str(projects), "--isci-log", str(isci_log),
             "--cikti-dizin", str(cikti_dizin), "--kutu", str(kutu)]
    komut.extend(ek)
    sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=300)
    return sonuc, cikti_dizin / (GUN + ".md")


JSON_RE = re.compile(r"<!--\s*MOTOR-RAPORU-JSON\s*(\{.*\})\s*-->")


def makine_blogu(metin):
    esles = JSON_RE.search(metin)
    if not esles:
        return None
    try:
        return json.loads(esles.group(1))
    except (json.JSONDecodeError, TypeError):
        return None


def ev_al(blok, ev):
    if not isinstance(blok, dict):
        return {}
    evler = blok.get("ev")
    if not isinstance(evler, dict):
        return {}
    deger = evler.get(ev)
    return deger if isinstance(deger, dict) else {}


def sayi(deger):
    try:
        return int(deger)
    except (TypeError, ValueError):
        return None


def vakalar(betik, kok):
    """(ad, gecti, aciklama) uretir. Ad = mutantin oldurdugunu gosterecegi ETIKET."""
    projects, isci_log, kutu = fikstur_kur(kok)
    kutu_once = kutu.read_bytes()
    sonuc, rapor = kosa(betik, kok, projects, isci_log, kutu)
    metin = rapor.read_text(encoding="utf-8") if rapor.is_file() else ""
    blok = makine_blogu(metin)

    pruvo = ev_al(blok, "pruvo")
    advisor = ev_al(blok, "pruvo-advisor")
    hasat = ev_al(blok, "pruvo-hasat")
    faralya = ev_al(blok, "faralya")
    toplam_kosum = 0
    if isinstance(blok, dict) and isinstance(blok.get("ev"), dict):
        for veri in blok["ev"].values():
            if isinstance(veri, dict):
                for anahtar in ("m3", "kimi", "deepseek", "claude_fallback",
                                "claude-fallback"):
                    toplam_kosum += sayi(veri.get(anahtar)) or 0

    cikti = []

    def vaka(ad, kosul, aciklama):
        cikti.append((ad, bool(kosul), aciklama))

    vaka("V01-rc-sifir", sonuc.returncode == 0,
         "rc=%d stderr=%r" % (sonuc.returncode, sonuc.stderr[-300:]))
    vaka("V02-rapor-diskte", rapor.is_file() and rapor.stat().st_size > 0,
         "yol=%s var=%s" % (rapor, rapor.is_file()))
    vaka("V03-makine-blogu", blok is not None,
         "MOTOR-RAPORU-JSON okunabildi=%s" % (blok is not None))
    vaka("V04-katlama-POZITIF", sayi(pruvo.get("claude")) == PRUVO_CLAUDE,
         "pruvo claude=%r beklenen=%d (33330 ana + 26 worktree + 4 alt-ajan; "
         "33330 gorulurse worktree KATLANMAMIS)"
         % (pruvo.get("claude"), PRUVO_CLAUDE))
    vaka("V05-katlama-NEGATIF",
         sayi(advisor.get("claude")) == ADVISOR_CLAUDE
         and sayi(pruvo.get("claude")) != PRUVO_CLAUDE + ADVISOR_CLAUDE,
         "pruvo-advisor claude=%r (ayri kalmali=%d); pruvo=%r (%d olursa advisor "
         "yutulmus)" % (advisor.get("claude"), ADVISOR_CLAUDE,
                        pruvo.get("claude"), PRUVO_CLAUDE + ADVISOR_CLAUDE))
    # 🔴 Bu vaka ONCE `"888888" not in metin` diye yazilmisti ve KORDU: rapor
    # sayilari Turkce binlik ayiracla basiyor ("888.888"), duz dizge aramasi
    # sizintiyi GORMEDI. Olcum makine-okunur bloktan yapilir; esik, katlama
    # farkindan (26+4) BAGIMSIZ secildi ki M1 bu vakayi yan-oldurmesin.
    pruvo_claude = sayi(pruvo.get("claude"))
    vaka("V06-gun-penceresi",
         pruvo_claude is not None and pruvo_claude < 500000,
         "pencere disi kayitlar (dun 999.999 · bugun 23:30 888.888) SIZMAMALI; "
         "pruvo claude=%r (pencere [00:00, 23:00) ise 500.000'in ALTINDA)"
         % pruvo.get("claude"))
    vaka("V07-model-kirilimi",
         sayi((pruvo.get("model") or {}).get("opus")) == PRUVO_OPUS
         and sayi((pruvo.get("model") or {}).get("sonnet")) == PRUVO_SONNET,
         "pruvo model=%r beklenen opus=%d sonnet=%d"
         % (pruvo.get("model"), PRUVO_OPUS, PRUVO_SONNET))
    vaka("V08-alt-ajan-ayri",
         sayi(pruvo.get("alt_ajan")) == 1 and sayi(pruvo.get("cip")) == 2,
         "pruvo cip=%r alt_ajan=%r beklenen 2 / 1"
         % (pruvo.get("cip"), pruvo.get("alt_ajan")))
    vaka("V09-kosum-BASLANGIC-birebir", toplam_kosum == BASLANGIC_PENCEREDE,
         "raporun toplam ucuz-kat kosumu=%d · penceredeki BASLANGIC=%d"
         % (toplam_kosum, BASLANGIC_PENCEREDE))
    vaka("V10-B-katlama-worktree-tabani", sayi(pruvo.get("m3")) == 1,
         "ev=aaa-111 (worktree taban adi) pruvo'ya katlanmali; pruvo m3=%r"
         % pruvo.get("m3"))
    vaka("V11-yarim-kosum-sayilir", sayi(hasat.get("m3")) == 2,
         "pruvo-hasat m3=%r beklenen 2 (BITIS'siz R4 dahil)" % hasat.get("m3"))
    vaka("V12-kimi-sayimi", sayi(faralya.get("kimi")) == 1,
         "faralya kimi=%r beklenen 1" % faralya.get("kimi"))
    vaka("V13-emekli-motor-gorunur", "deepseek" in metin,
         "emekli motor kosumu raporda gorunmeli")
    vaka("V14-kirmizi-isaret",
         "🔴" in metin and re.search(r"pruvo-advisor.*🔴", metin) is not None,
         "pruvo-advisor: claude>0 ama ucuz kat 0 -> 🔴 isareti bekleniyor")
    vaka("V15-bozuk-json-cokertmez",
         sonuc.returncode == 0
         and sayi((pruvo.get("model") or {}).get("opus")) == PRUVO_OPUS,
         "bozuk JSON satiri kosumu dusurmemeli ve AYNI DOSYADAKI sonraki "
         "kayitlari yutmamali (opus=%r beklenen %d)"
         % ((pruvo.get("model") or {}).get("opus"), PRUVO_OPUS))
    vaka("V16-kutu-yazilmadi", kutu.read_bytes() == kutu_once,
         "--kutu-yaz VERILMEDEN kutu degismemeli (%d -> %d bayt)"
         % (len(kutu_once), len(kutu.read_bytes())))

    # --kutu-yaz KOLU: ayri kosum, ayri fikstur kutusu
    sonuc2, rapor2 = kosa(betik, kok, projects, isci_log, kutu, ek=["--kutu-yaz"])
    kutu_sonra = kutu.read_text(encoding="utf-8")
    yeni_satirlar = kutu_sonra.splitlines()
    eski_satirlar = kutu_once.decode("utf-8").splitlines()
    eklenen = len(yeni_satirlar) - len(eski_satirlar)
    vaka("V17-kutu-blogu-25-satir-alti", 0 < eklenen <= 25,
         "kutuya eklenen satir=%d (0 < N <= 25 olmali)" % eklenen)
    vaka("V18-kutu-silme-yok",
         all(satir in yeni_satirlar for satir in eski_satirlar),
         "mevcut kutu icerigi KORUNMALI (silme yok)")
    vaka("V19-motor-orani-satiri", "MOTOR ORANI:" in kutu_sonra,
         "kutu blogunda zorunlu MOTOR ORANI satiri")

    # 🔴 V20 — AYNI GUNUN BLOGU IKI KEZ EKLENEMEZ. Ozdes baslik,
    # `kutu-arsivle.py`nin "blok tam olarak BIR KEZ bulunur" degismezini curutur;
    # rotasyon rc=1 doner ve kota kapisi TUM EVIN commitini kilitler. 2 Eyl'de
    # CANLI olarak olculdu (kutu 221 -> 260, iki ozdes baslik, commit DURDU).
    baslik = "## %s — 📊 GÜNLÜK MOTOR RAPORU (23:00)" % GUN
    kosa(betik, kok, projects, isci_log, kutu, ek=["--kutu-yaz"])
    kutu_ucuncu = kutu.read_text(encoding="utf-8")
    baslik_n = kutu_ucuncu.count(baslik)
    vaka("V20-ayni-gun-blogu-cogalmaz",
         baslik_n == 1 and len(kutu_ucuncu.splitlines()) == len(yeni_satirlar),
         "ikinci `--kutu-yaz` blogu COGALTMAMALI, DEGISTIRMELI: baslik=%d "
         "(1 olmali) · satir %d -> %d (ayni olmali)"
         % (baslik_n, len(yeni_satirlar), len(kutu_ucuncu.splitlines())))
    vaka("V21-tekrar-yazimda-silme-yok",
         all(satir in kutu_ucuncu.splitlines() for satir in eski_satirlar),
         "tekrar yazimda da mevcut kutu icerigi KORUNMALI")
    return cikti


# --- MUTANTLAR ---------------------------------------------------------------
# Her mutant: (ad, uygula(metin) -> metin|None, oldurmesi_beklenen_vaka)
# oldurmesi_beklenen_vaka None ise ESDEGER KONTROL mutantidir: HICBIR vakayi
# oldurmemelidir.

# Capalar CANLI GOVDEDEN alindi ([[mutant-canli-govdede-yasamaz]] /
# [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]): her mutant
# GERCEKTEN kosulan bir satiri degistirir, imzayi/yorumu degil.

CAPA_KATLAMA = "    i = dizin_adi.find(AYIRICI)"
CAPA_KOK = "    kok = dizin_adi[:i] if i > 0 else dizin_adi"
CAPA_YARIM = '    e["kosum_listesi"].append(kosum_bilgi)'


def _tekil(metin, capa, yerine):
    if metin.count(capa) != 1:
        return None
    return metin.replace(capa, yerine, 1)


def m_katlama_kapat(metin):
    """Katlama KAPANIR: worktree dizini ayri ev sayilir -> POZITIF kol duser."""
    return _tekil(metin, CAPA_KATLAMA,
                  "    i = -1  # MUTANT-M1: katlama kapali")


def m_katlama_onek(metin):
    """Ayirici bulunamayinca ON-EK ile katla: `-pruvo-advisor` PRUVO'ya YUTULUR.
    Worktree katlamasi CALISMAYA DEVAM EDER -> yalniz NEGATIF kol dusmeli."""
    return _tekil(
        metin, CAPA_KOK,
        "    _onek = EV_ON_EKI + 'pruvo'  # MUTANT-M2: cikplak on-ek ile katlama\n"
        "    if i > 0:\n"
        "        kok = dizin_adi[:i]\n"
        "    elif dizin_adi.startswith(_onek):\n"
        "        kok = _onek\n"
        "    else:\n"
        "        kok = dizin_adi")


def m_pencere_tam_gun(metin):
    """Pencere sonu 23:00 yerine 00:00 (ertesi gun): 23:30 kaydi SIZAR."""
    for saat in ("dt.time(23, 0, 0)", "dt.time(23, 0)"):
        capa = "    son = dt.datetime.combine(t, %s, tzinfo=yerel)" % saat
        if metin.count(capa) == 1:
            return metin.replace(
                capa,
                "    son = dt.datetime.combine(t + dt.timedelta(days=1), "
                "dt.time(0, 0, 0), tzinfo=yerel)  # MUTANT-M3", 1)
    return None


def m_yarim_kosum(metin):
    """BITIS'siz kosum SAYILMAZ -> BASLANGIC birebirligi duser."""
    return _tekil(
        metin, CAPA_YARIM,
        '    if aktif.get("rc") is not None:  # MUTANT-M4: yarim kosum atlanir\n'
        '        e["kosum_listesi"].append(kosum_bilgi)\n'
        '    else:\n'
        '        return')


def m_esdeger_kontrol(metin):
    """ESDEGER KONTROL: davranissiz (yorum + kullanilmayan sabit).
    HICBIR vakayi oldurmemeli; oldururse batarya AMBIYANS olcuyor demektir."""
    capa = "AYIRICI = "
    if metin.count(capa) < 1:
        return None
    return metin.replace(
        capa,
        "_MUTANT_M5_KONTROL = 'davranissiz'  # esdeger kontrol mutanti\n" + capa,
        1)


def m_kutu_hep_ekle(metin):
    """DEGISTIR kolu kapanir: ayni gunun blogu HER kosumda yeniden EKLENIR.
    2 Eyl'de canli olan ariza budur — iki ozdes baslik `kutu-arsivle.py`nin
    lossless degismezini curutur, rotasyon rc=1, TUM EVIN commiti kilitlenir."""
    capa = "    bulunan_idx = mevcut.find(baslik)"
    if metin.count(capa) != 1:
        return None
    return metin.replace(
        capa,
        "    bulunan_idx = -1  # MUTANT-M6: degistirme kapali, hep ekle\n"
        "    _capa = mevcut.find(baslik)", 1)


MUTANTLAR = [
    ("M6-kutu-degistirme-kapali", m_kutu_hep_ekle, "V20-ayni-gun-blogu-cogalmaz"),
    ("M1-katlama-kapali", m_katlama_kapat, "V04-katlama-POZITIF"),
    ("M2-katlama-cikplak-onek", m_katlama_onek, "V05-katlama-NEGATIF"),
    ("M3-pencere-tam-gun", m_pencere_tam_gun, "V06-gun-penceresi"),
    ("M4-yarim-kosum-sayilmaz", m_yarim_kosum, "V09-kosum-BASLANGIC-birebir"),
    ("M5-ESDEGER-KONTROL", m_esdeger_kontrol, None),
]


def kabul_kolu(betik):
    with tempfile.TemporaryDirectory(prefix="motor-rapor-kabul-") as gecici:
        sonuclar = vakalar(betik, Path(gecici))
    gecen = sum(1 for _, ok, _ in sonuclar if ok)
    print("== KABUL ==")
    for ad, ok, aciklama in sonuclar:
        print("  %s %-32s %s" % ("YESIL" if ok else "KIRMIZI", ad,
                                 "" if ok else aciklama))
    print("KABUL %d/%d" % (gecen, len(sonuclar)))
    return sonuclar


def mutasyon_kolu(betik, taban_sonuc):
    taban_gecen = {ad for ad, ok, _ in taban_sonuc if ok}
    print("== MUTASYON ==")
    rapor = []
    for ad, uygula, hedef in MUTANTLAR:
        kaynak = betik.read_text(encoding="utf-8")
        mutant_metin = uygula(kaynak)
        if mutant_metin is None or mutant_metin == kaynak:
            print("  UYGULANMADI %-28s (capa bulunamadi — SURVIVOR DEGIL)" % ad)
            rapor.append((ad, "UYGULANMADI", hedef, set()))
            continue
        with tempfile.TemporaryDirectory(prefix="motor-rapor-mut-") as gecici:
            kok = Path(gecici)
            mutant = kok / "mutant.py"
            mutant.write_text(mutant_metin, encoding="utf-8")
            try:
                sonuc = vakalar(mutant, kok / "is")
            except Exception as hata:                     # noqa: BLE001
                sonuc = [("V00-COKME", False, repr(hata))]
        dusen = {vaka for vaka, ok, _ in sonuc if not ok and vaka in taban_gecen}
        dusen |= {vaka for vaka, ok, _ in sonuc if not ok and vaka == "V00-COKME"}
        if hedef is None:
            durum = "YESIL" if not dusen else "KIRMIZI"
            print("  %s %-28s ESDEGER KONTROL — dusen vaka: %s"
                  % (durum, ad, sorted(dusen) or "YOK (beklenen)"))
        elif hedef in dusen:
            print("  YESIL   %-28s OLDURDUGU VAKA: %s   (yan dusen: %s)"
                  % (ad, hedef, sorted(dusen - {hedef}) or "yok"))
        else:
            print("  SURVIVOR %-27s hedef %s DUSMEDI (dusen: %s)"
                  % (ad, hedef, sorted(dusen) or "hicbiri"))
        rapor.append((ad, "KOSTU", hedef, dusen))
    return rapor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--betik", default=str(HEDEF))
    ap.add_argument("--python", default=None,
                    help="olculecek betigi bu yorumlayiciyla kos "
                         "(cron satirinin yorumlayicisi: /usr/bin/python3)")
    ap.add_argument("--kabul", action="store_true")
    ap.add_argument("--mutasyon", action="store_true")
    args = ap.parse_args()
    python_ayarla(args.python)
    print("YORUMLAYICI=%s" % PYTHON)

    betik = Path(args.betik)
    if not betik.is_file():
        print("OLCULEMEDI: betik yok: %s" % betik, file=sys.stderr)
        return 2

    hepsi = not (args.kabul or args.mutasyon)
    taban = []
    if args.kabul or hepsi:
        taban = kabul_kolu(betik)
    mut = []
    if args.mutasyon or hepsi:
        if not taban:
            taban = kabul_kolu(betik)
        mut = mutasyon_kolu(betik, taban)

    kirmizi = [ad for ad, ok, _ in taban if not ok]
    survivor = [ad for ad, durum, hedef, dusen in mut
                if durum == "KOSTU" and hedef is not None and hedef not in dusen]
    uygulanmadi = [ad for ad, durum, _, _ in mut if durum == "UYGULANMADI"]
    esdeger_kirli = [ad for ad, durum, hedef, dusen in mut
                     if durum == "KOSTU" and hedef is None and dusen]
    print("== OZET ==")
    print("KIRMIZI_VAKA=%d %s" % (len(kirmizi), kirmizi))
    print("SURVIVOR=%d %s" % (len(survivor), survivor))
    print("UYGULANMADI=%d %s" % (len(uygulanmadi), uygulanmadi))
    print("ESDEGER_KONTROL_KIRLI=%d %s" % (len(esdeger_kirli), esdeger_kirli))
    return 1 if (kirmizi or survivor or uygulanmadi or esdeger_kirli) else 0


if __name__ == "__main__":
    sys.exit(main())
