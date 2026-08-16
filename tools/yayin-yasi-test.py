#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN YASI NOBETCISI — KABUL TESTI (AG YOK) + MUTASYON BATARYASI.

Iki kol tek girdiden kosar (`python3 tools/yayin-yasi-test.py`, bayrak YOK):

  A) KABUL   — hukum fonksiyonu (`degerlendir`) + kenar katmanin ayristiricilari
               (`zaman_ayristir`, `son_basarili_dagitim`, `kiyasla`) SAHTE api ile.
               DIS AG YOKTUR: her vaka sabit fikstur uzerinde kosar.
  B) MUTASYON— nobetcinin KAYNAGI bellekte bozulur ve ayni kabul vakalari
               yeniden kosulur. Her mutant EN AZ BIR vakayi kirmizi yakmalidir;
               yakmayan mutant SURVIVOR'dir ve bu test KIRMIZI biter.
               ([[mutasyon-kaniti-yeniden-uretilebilir]] — anlatilan batarya kanit
               degildir; batarya BURADA kosar.)  Mutasyon DISKE YAZILMAZ:
               kaynak metni bellekte degistirilip taze modul olarak exec edilir
               ([[mutasyon-diske-yazma-tuzagi]] · [[mutasyon-bytecode-onbellegi]]).

🔴 MUTANT UYGULANMADI = KIRMIZI: her mutasyonun capasi kaynakta ARANIR; capa
bulunamazsa (kod degisti, mutasyon artik baska yere basiyor) test yesil GECMEZ.
"""
import os
import sys
import types
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "yayin-yasi-nobetcisi.py")

SIMDI = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)


def _yukle(kaynak=None, ad="_yayin_yasi_sut"):
    """Nobetciyi TAZE bir modul olarak yukler (bellekten; diske yazmaz)."""
    if kaynak is None:
        with open(HEDEF, encoding="utf-8") as f:
            kaynak = f.read()
    m = types.ModuleType(ad)
    m.__file__ = HEDEF
    exec(compile(kaynak, HEDEF, "exec"), m.__dict__)            # noqa: S102
    return m


def _dagitim(mod, saat_once, sha="268da994aaaa"):
    return {"sha": sha, "id": 1, "olusma": SIMDI - timedelta(hours=saat_once)}


def _kiyas(durum="ahead", ileri=1, geri=0, yas_saat=None, sha="7a695700bbbb"):
    return {"durum": durum, "ileri": ileri, "geri": geri,
            "en_eski": None if yas_saat is None else SIMDI - timedelta(hours=yas_saat),
            "en_eski_sha": sha}


class _SahteApi:
    """Yol -> yanit sozlugu. Bilinmeyen yol -> KeyError (sessiz bos liste YOK)."""

    def __init__(self, tablo):
        self.tablo = tablo
        self.cagrilar = []

    def __call__(self, yol):
        self.cagrilar.append(yol)
        for anahtar, deger in self.tablo.items():
            if anahtar in yol:
                return deger
        raise KeyError(yol)


# ════════════════════════════════════════════════════════ KABUL VAKALARI
def vakalar(mod):
    """[(ad, gecti_mi, detay)] — mutant modul de AYNI listeyi kosar."""
    ok = []

    def iddia(ad, kosul, detay=""):
        ok.append((ad, bool(kosul), detay))

    def hukum(dagitim, kiyas, **kw):
        s, rc, satir, ozet = mod.degerlendir(dagitim, kiyas, SIMDI, **kw)
        return s, rc, ozet, " ".join(satir)

    # ---- K1 KONTROL: sessiz gece KUSUR DEGIL (yanlis-pozitif kapisi) --------
    s, rc, _o, _t = hukum(_dagitim(mod, 40), _kiyas(durum="identical", ileri=0))
    iddia("K1 canli == main ucu, dagitim 40 SAATLIK -> ACIK (sakin gece kirmizi yakmaz)",
          s == "ACIK" and rc == 0, "%s rc=%d" % (s, rc))

    # ---- K2 OLDURUCU: 15-16 Agu olayinin BIREBIR fiksturu -------------------
    s, rc, ozet, _t = hukum(_dagitim(mod, 21), _kiyas(ileri=22, yas_saat=21))
    iddia("K2 OLAY: 22 commit yayina girmemis, en eskisi 21 SAATLIK -> BAYAT (rc 1)",
          s == "BAYAT" and rc == 1, "%s rc=%d" % (s, rc))
    iddia("K2b bekleyen commit sayisi RAPORLANIR (22)", ozet.get("bekleyen") == 22,
          str(ozet.get("bekleyen")))

    # ---- K3 AYIRT EDICI: hukum DAGITIMIN yasindan DEGIL, BEKLEYENIN yasindan -
    s, rc, _o, _t = hukum(_dagitim(mod, 30), _kiyas(ileri=3, yas_saat=0.33))
    iddia("K3 dagitim 30 saatlik ama bekleyen en eski commit 20 DK -> ACIK "
          "(olculen buyukluk BEKLEYENIN yasi)", s == "ACIK" and rc == 0,
          "%s rc=%d" % (s, rc))

    # ---- K4/K5 SINIR: tavan DAHILDIR ---------------------------------------
    s4, rc4, _o, _t = hukum(_dagitim(mod, 5), _kiyas(ileri=1, yas_saat=mod.TAVAN_SAAT))
    iddia("K4 yas TAM tavan (%.1f sa) -> BAYAT (esik dahil)" % mod.TAVAN_SAAT,
          s4 == "BAYAT" and rc4 == 1, "%s rc=%d" % (s4, rc4))
    s5, rc5, _o, _t = hukum(_dagitim(mod, 5),
                            _kiyas(ileri=1, yas_saat=mod.TAVAN_SAAT - (1.0 / 3600.0)))
    iddia("K5 yas tavanin 1 SN altinda -> ACIK", s5 == "ACIK" and rc5 == 0,
          "%s rc=%d" % (s5, rc5))

    # ---- K6-K10 FAIL-CLOSED KOLLARI (hepsi rc 2, SESSIZ YESIL YOK) ---------
    # 🔴 rc 2 TEK BASINA YETMEZ: dort ayri ariza da rc 2 verir; TANI da olculur,
    # yoksa "yanlis sebeple dogru cikis kodu" mutantlari SURVIVOR olur.
    s, rc, _o, tani = hukum(None, _kiyas(ileri=5, yas_saat=99))
    iddia("K6 basarili dagitim kaydi YOK -> OLCULEMEDI (rc 2) + dogru tani",
          s == "OLCULEMEDI" and rc == 2 and "dagitim kaydi YOK" in tani,
          "%s rc=%d" % (s, rc))

    for durum in ("behind", "diverged"):
        s, rc, _o, tani = hukum(_dagitim(mod, 2), _kiyas(durum=durum, ileri=0, geri=4))
        iddia("K7 dagitilan SHA dal gecmisinde degil (%s) -> OLCULEMEDI + 'gecmisinde "
              "DEGIL' tanisi" % durum,
              s == "OLCULEMEDI" and rc == 2 and "gecmisinde DEGIL" in tani,
              "%s rc=%d | %s" % (s, rc, tani[:60]))

    s, rc, _o, tani = hukum(_dagitim(mod, 2), _kiyas(durum="mars", ileri=1, yas_saat=99))
    iddia("K8 kiyas durumu BILINMIYOR -> OLCULEMEDI (rc 2)",
          s == "OLCULEMEDI" and rc == 2 and "BILINMIYOR" in tani, "%s rc=%d" % (s, rc))

    s, rc, _o, tani = hukum(_dagitim(mod, 2), _kiyas(ileri=9, yas_saat=None))
    iddia("K9 bekleyen VAR ama tarihi okunamadi -> OLCULEMEDI (tarihsiz commit "
          "'taze' SAYILMAZ)",
          s == "OLCULEMEDI" and rc == 2 and "TARIHI okunamadi" in tani,
          "%s rc=%d" % (s, rc))

    s, rc, _o, tani = hukum(_dagitim(mod, 2), _kiyas(ileri=1, yas_saat=-5))
    iddia("K10 bekleyen commit GELECEK tarihli -> OLCULEMEDI (rc 2)",
          s == "OLCULEMEDI" and rc == 2 and "GELECEK" in tani, "%s rc=%d" % (s, rc))

    # ---- K11 DAGITIM SECIMI: 'success' DISI durum YAYIN DEGILDIR -----------
    api = _SahteApi({
        "/deployments?": [{"id": 9, "sha": "yeni9", "created_at": "2026-08-16T11:00:00Z"},
                          {"id": 8, "sha": "eski8", "created_at": "2026-08-15T14:02:00Z"}],
        "/deployments/9/statuses": [{"state": "in_progress"}, {"state": "failure"}],
        "/deployments/8/statuses": [{"state": "success"}],
    })
    try:
        d = mod.son_basarili_dagitim("o/r", "jeton", api=api)
        iddia("K11 en yeni dagitim BASARISIZ -> bir onceki BASARILI kayit secilir",
              d.get("sha") == "eski8", str(d.get("sha")))
    except Exception as e:                                      # noqa: BLE001
        iddia("K11 en yeni dagitim BASARISIZ -> bir onceki BASARILI kayit secilir",
              False, "istisna: %s" % e)

    api2 = _SahteApi({
        "/deployments?": [{"id": 9, "sha": "yeni9", "created_at": "2026-08-16T11:00:00Z"}],
        "/deployments/9/statuses": [{"state": "in_progress"}],
    })
    try:
        mod.son_basarili_dagitim("o/r", "jeton", api=api2)
        iddia("K12 hicbir dagitim 'success' degil -> OlcumHatasi (rc 2 kolu)", False,
              "istisna ATILMADI")
    except mod.OlcumHatasi:
        iddia("K12 hicbir dagitim 'success' degil -> OlcumHatasi (rc 2 kolu)", True)
    except Exception as e:                                      # noqa: BLE001
        iddia("K12 hicbir dagitim 'success' degil -> OlcumHatasi (rc 2 kolu)", False,
              "yanlis istisna: %s" % type(e).__name__)

    # 🔴 TANI DA OLCULUR: bos liste ile "hicbiri success degil" AYRI arizalardir;
    # ikisi de OlcumHatasi atar, tani ayrilmazsa kontrol kolu SURVIVOR uretir.
    api3 = _SahteApi({"/deployments?": []})
    _ad13 = "K13 dagitim listesi BOS -> OlcumHatasi + 'HIC dagitim kaydi yok' tanisi"
    try:
        mod.son_basarili_dagitim("o/r", "jeton", api=api3)
        iddia(_ad13, False, "istisna ATILMADI")
    except mod.OlcumHatasi as e:
        iddia(_ad13, "HIC dagitim kaydi yok" in str(e), str(e)[:60])
    except Exception as e:                                      # noqa: BLE001
        iddia(_ad13, False, "yanlis istisna: %s" % type(e).__name__)

    # ---- K14 COMPARE AYRISTIRMASI: en ESKI commit commits[0]'dir ------------
    api4 = _SahteApi({"/compare/": {
        "status": "ahead", "ahead_by": 2, "behind_by": 0,
        "commits": [{"sha": "eski", "commit": {"committer":
                                               {"date": "2026-08-15T14:30:00Z"}}},
                    {"sha": "yeni", "commit": {"committer":
                                               {"date": "2026-08-16T09:00:00Z"}}}]}})
    k = mod.kiyasla("o/r", "jeton", "taban", api=api4)
    iddia("K14 compare: en ESKI bekleyen commit commits[0]'dan turer",
          k.get("en_eski_sha") == "eski"
          and k.get("en_eski") == datetime(2026, 8, 15, 14, 30, tzinfo=timezone.utc),
          "%s %s" % (k.get("en_eski_sha"), k.get("en_eski")))

    # ---- K15 ZAMAN AYRISTIRMA ----------------------------------------------
    iddia("K15a 'Z' ekli damga UTC olarak okunur",
          mod.zaman_ayristir("2026-08-15T14:02:00Z")
          == datetime(2026, 8, 15, 14, 2, tzinfo=timezone.utc))
    iddia("K15b ofsetli damga UTC'ye cevrilir",
          mod.zaman_ayristir("2026-08-15T17:02:00+03:00")
          == datetime(2026, 8, 15, 14, 2, tzinfo=timezone.utc))
    for bozuk in ("", "   ", "dun", None):
        try:
            mod.zaman_ayristir(bozuk)
            iddia("K15c bozuk damga (%r) -> OlcumHatasi" % (bozuk,), False,
                  "istisna ATILMADI")
        except mod.OlcumHatasi:
            iddia("K15c bozuk damga (%r) -> OlcumHatasi" % (bozuk,), True)
        except Exception as e:                                  # noqa: BLE001
            iddia("K15c bozuk damga (%r) -> OlcumHatasi" % (bozuk,), False,
                  "yanlis istisna: %s" % type(e).__name__)

    # ---- K16 UCTAN UCA: OlcumHatasi rc 2'ye cevrilir, patlamaz -------------
    def _patlat(*a, **kw):
        raise mod.OlcumHatasi("sahte ariza")

    eski = mod.son_basarili_dagitim
    eski_jeton = mod._jeton
    eski_depo = mod._depo
    try:
        mod._jeton = lambda cevre=None: "jeton"
        mod._depo = lambda cevre=None, kok=None: "o/r"
        mod.son_basarili_dagitim = _patlat
        s, rc, satirlar, _ = mod.olc()
        iddia("K16 olc(): API arizasi rc 2'ye cevrilir (istisna SIZMAZ)",
              s == "OLCULEMEDI" and rc == 2 and any("OLCULEMEDI" in x for x in satirlar),
              "%s rc=%d" % (s, rc))
    finally:
        mod.son_basarili_dagitim = eski
        mod._jeton = eski_jeton
        mod._depo = eski_depo

    return ok


# ════════════════════════════════════════════════════════════ MUTASYONLAR
# (capa, yerine, neyi bozar) — her biri EN AZ BIR kabul vakasini kirmizi yakmali.
MUTASYONLAR = [
    ('TAVAN_SAAT = 3.0', 'TAVAN_SAAT = 72.0',
     "esigi olayin suresinin ustune cikarir (21 saat sessiz gecerdi)"),
    ('if yas >= ozet["tavan_sn"]:', 'if yas > ozet["tavan_sn"] * 2:',
     "esik karsilastirmasi gevsetilir"),
    ('yas = (simdi - en_eski).total_seconds()',
     'yas = (simdi - dagitim["olusma"]).total_seconds()',
     "hukum BEKLEYENIN degil DAGITIMIN yasindan verilir (sakin gece yanlis alarm)"),
    ('    if yas < 0:', '    if False:',
     "negatif yas (saat/damga arizasi) sessizce 'cok taze' sayilir"),
    ('    if en_eski is None:', '    if en_eski is None and False:',
     "tarihi okunamayan bekleyen commit 'taze' sayilir"),
    ('    if durum in ("behind", "diverged"):', '    if False:',
     "force-push/yabanci SHA dagitimi sessizce hukum uretir"),
    ('BASARI_DURUMU = "success"', 'BASARI_DURUMU = "in_progress"',
     "yayin sayilan durum gevsetilir (akmamis dagitim 'yayin' sayilir)"),
    ('if any((d or {}).get("state") == BASARI_DURUMU for d in durumlar):',
     'if True:',
     "dagitim KAYDININ varligi 'yayin oldu' sayilir (durum kaydi okunmaz)"),
    ('    if not kayitlar:', '    if False:',
     "bos dagitim listesi tanisiz gecer"),
]


def mutasyon_kolu(kaynak):
    """[(etiket, sonuc, detay)] — sonuc: OLDU | SURVIVOR | UYGULANMADI."""
    sonuc = []
    for capa, yerine, neden in MUTASYONLAR:
        etiket = "%s  ->  %s" % (capa.strip(), yerine.strip())
        if kaynak.count(capa) != 1:
            sonuc.append((etiket, "UYGULANMADI",
                          "capa kaynakta %d kez bulundu (1 olmali)" % kaynak.count(capa)))
            continue
        try:
            mutant = _yukle(kaynak.replace(capa, yerine), ad="_yayin_yasi_mutant")
        except Exception as e:                                  # noqa: BLE001
            sonuc.append((etiket, "OLDU", "mutant yuklenemedi (%s)" % type(e).__name__))
            continue
        try:
            dusenler = [ad for ad, gecti, _d in vakalar(mutant) if not gecti]
        except Exception as e:                                  # noqa: BLE001
            dusenler = ["istisna: %s" % type(e).__name__]
        if dusenler:
            sonuc.append((etiket, "OLDU", "%d vaka kirmizi (%s)"
                          % (len(dusenler), dusenler[0][:52])))
        else:
            sonuc.append((etiket, "SURVIVOR", "HICBIR vaka yakalamadi — %s" % neden))
    return sonuc


def main():
    with open(HEDEF, encoding="utf-8") as f:
        kaynak = f.read()

    print("YAYIN YASI NOBETCISI — KABUL (A) + MUTASYON (B).  DIS AG YOK.")
    print("=" * 78)
    print("A) KABUL")
    sonuclar = vakalar(_yukle(kaynak))
    for ad, gecti, detay in sonuclar:
        print(("  ✔ " if gecti else "  ✘ ") + ad + (("   [%s]" % detay) if detay else ""))
    dusen = [ad for ad, gecti, _ in sonuclar if not gecti]

    print("")
    print("B) MUTASYON (kaynak BELLEKTE bozulur, ayni vakalar yeniden kosar)")
    mut = mutasyon_kolu(kaynak)
    for etiket, durum, detay in mut:
        isaret = {"OLDU": "  ☠ ", "SURVIVOR": "  ✘ ", "UYGULANMADI": "  ✘ "}[durum]
        print("%s%-9s %s" % (isaret, durum, etiket))
        if durum != "OLDU":
            print("        %s" % detay)
    survivor = [e for e, d, _ in mut if d == "SURVIVOR"]
    uygulanmadi = [e for e, d, _ in mut if d == "UYGULANMADI"]

    print("")
    print("KABUL %d/%d · MUTASYON %d/%d OLDU · SURVIVOR=%d · UYGULANMADI=%d"
          % (len(sonuclar) - len(dusen), len(sonuclar),
             len(mut) - len(survivor) - len(uygulanmadi), len(mut),
             len(survivor), len(uygulanmadi)))
    if dusen or survivor or uygulanmadi:
        print("SONUC: KIRMIZI")
        return 1
    print("SONUC: YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
