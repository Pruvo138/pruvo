#!/usr/bin/env python3
"""yetim-kayit-kapisi.py — KAYNAK KAYDI OLMAYAN + BASLIK-TUREVI R2 ANAHTARI (yetim) kapisi.

NEDEN (K55, 12 Agu 2026 — MaCiT→Tamirci): 10 canli Mercedes urunu `.urun-kaynaklari.json`
kaydi OLMADAN ve R2 anahtarlari kaynak-id (th/pr/mw/cgt/c3d) yerine BASLIK-slug'undan
turetilmis halde yayina girdi. Mevcut yol-dedup bunlari GOREMIYORDU:
  * `tools/gorsel-cakisma-onar.py` yalniz URL CAKISAN urunleri tarar (iki urun AYNI
    anahtari paylasanlar) -> cakismayan yetim sessizce disinda kalir.
  * `tools/mukerrer-kontrol.py` yalniz mukerrer ID/BASLIK/KAYNAK-linki tarar -> kaydi
    OLMAYAN urunun linki "" oldugu icin kaynak eksenine hic girmez.
Sonuc: bu urunler hicbir onarim/dedup yuzeyinde gorunmez; baslik-turevi anahtar tasidigi
icin [[gorsel-anahtar-cakismasi]] sinifinin (18 Tem 2026, 143 urun) MUHATARASI acik kalir
(ayni basligi uretecek bir sonraki urun ayni anahtari ezer).

SINIF IZASI (kaynak anahtari [[tekil-yama-sinifi-kapatmaz]]): kayit-YOK + anahtar kaynak-id
desenine UYMAYAN (baslik-turevi) + parametrik != True. Bu uc kosulun UCU birden varsa yetim.
  * kayit VAR  -> izlenebilir (ayri duzlem), yetim DEGIL.
  * anahtar kaynak-id desenli -> catisma riski YOK (kaynak-id benzersizdir), ayri sinif
    (kayit eksikligi/hijyen; raporlanir ama KIRMIZI yanmaz).
  * parametrik=True (sari/olcuye-ozel seri) -> gorseli yok ya da baslik-turevi anahtar
    MESRU; bu seri kaynak-id'den uretilmez, tarama disidir.

KULLANIM (salt-okunur; hicbir dosyaya YAZMAZ, .urun-kaynaklari.json ICERIGINI basmaz):
    python3 tools/yetim-kayit-kapisi.py                # canli katalog taramasi
    python3 tools/yetim-kayit-kapisi.py --kendini-test # uydurma fiksturde sinama (ag yok)

CIKIS KODU: 0 = yetim yok VE siniflandirici/self-test yesil VE iddia tabani dusmedi;
1 = yetim var ya da siniflandirici/self-test kirmizi; 2 = katalog/kaynak dosyasi
okunamadi (FAIL-CLOSED OLCULEMEDI).

🔴 BUGUN KIRMIZI YANAR (12 Agu 2026 olcumu: 192 yetim). Bu DOGRU davranistir: kapi onu
DUZELTMEZ, GORUR — veri tek-yazar MaCiT duzlemidir, kapi yalniz sinifi sessiz birikmekten
alikoyar. Yetim sayisi ancak MaCiT'in backfill'iyle (kayit + kaynak-id anahtara yeniden
yukleme) duser; kapi esik DUSURMEZ, muafiyet listesi TUTMAZ (kuraldan turer -> drift yok).
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("PRUVO_ROOT") or os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
URUNLER = os.environ.get("PRUVO_URUNLER_JSON") or os.path.join(ROOT, "urunler.json")
KAYNAK = os.environ.get("PRUVO_KAYNAKLAR_JSON") or os.path.join(ROOT, ".urun-kaynaklari.json")

# ───────────────────────────────────────────── KAPININ BEKLENTI CAPALARI (frozen, turetilmez)
# 🔴 r2_anahtar'dan TURETILMEZ — turetilseydi A1 totolojiye donerdi. Ayrisma A1'de ACIKCA
# olculur; canlida YENI bir platform onegi eklense (or. "pv") kapi sessizce korlesmez, A1
# kirmizi yanar ve siniflandirici o onegi bilmedigini SOYLER.
# 🔴 DEGER-KUMESI biciminde tutulur (platform ADI -> onek haritasi DEGIL): r2-onek-gelenek-
# kapisi E1, "Cults3D"->"c3d" satir-ici KOPYAYI yasaklar (ayri kaynak ilkesi); burada yalniz
# onek DEGERLERI donup A1'de r2_anahtar.ONEKLER.values() ile karsilastirilir — kopya DEGIL.
BEKLENEN_ONEKLER_DEGERLERI = ("c3d", "cgt", "mw", "pr", "th")

#: kaynak-id desenli anahtar: th/pr/mw/cgt (+tarihsel cgt-) icin SAYISAL govde, c3d icin slug.
#: Baslik-turevi anahtar (mercedes-…, bmw-…, volvo-…) bu desene UYMAZ -> yetim adayidir.
KAYNAK_ID_RE = re.compile(r"^(th\d+|pr\d+|mw\d+|cgt-?\d+|c3d[a-z0-9-]+)$")

#: 🔴 TARAMA YUZEYI TABANI — kapi kac kayda BAKTIGININ alt siniri. Yuzey sessizce kuculurse
#: "yetim yok" iddiasi BOSALIR. 12 Agu 2026 olcumu: 26781 kayit.
TARAMA_TABANI_KAYIT = 20000

#: 🔴 IDDIA TABANI — kosmasi gereken en az iddia sayisi (DUSURMEK = sessiz korluk).
IDDIA_TABANI = 4

hatalar = []
olculemedi = []
_iddialar = []


def sonuc(kimlik, ad, ok, detay=""):
    _iddialar.append((kimlik, ok))
    print("  %-10s %s. %s%s" % ("OK" if ok else "KIRMIZI", kimlik, ad,
                                ("  -> " + str(detay)) if detay else ""))
    if not ok:
        hatalar.append(kimlik)


def olcum_yok(kimlik, ad, detay=""):
    _iddialar.append((kimlik, True))
    olculemedi.append(kimlik)
    print("  %-10s %s. %s%s" % ("OLCULEMEDI", kimlik, ad,
                                ("  -> " + str(detay)) if detay else ""))


def _load_r2k():
    yol = os.path.join(TOOLS, "r2_anahtar.py")
    spec = importlib.util.spec_from_file_location("r2_anahtar_yetim", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


r2k = _load_r2k()

# ─────────────────────────────────────────────────────────────── siniflandirici (TEK kopya)
def _kaynak_id_mi(anahtar):
    """R2 anahtari kaynak-id desenli mi? TEK siniflandirici — tarama ve pozitif/negatif
    kontrol AYNI fonksiyonu kullanir (ayri kopya = ikiz = sessiz ayrisma)."""
    return bool(KAYNAK_ID_RE.match(anahtar or ""))


def _ilk_anahtar(gorseller):
    """gorseller[] icinden cozulebilen ILK R2 anahtari (yoksa None). Deterministik."""
    for g in (gorseller or []):
        a, _n = r2k.anahtar_coz(g)
        if a:
            return a
    return None


def _tara(urunler, kaynaklar):
    """(yetim, kayit_yok_kaynakid) — yetim = kayit-YOK + baslik-turevi anahtar + non-parametrik.

    kaynaklar None ise (dosya okunamadi) None dondurur -> cagiran FAIL-CLOSED karar verir.
    """
    if kaynaklar is None:
        return None, None
    yetim = []
    kayit_yok_kaynakid = []
    for u in urunler or []:
        if not isinstance(u, dict):
            continue
        if u.get("parametrik") is True:
            continue
        pid = u.get("id")
        anahtar = _ilk_anahtar(u.get("gorseller"))
        if anahtar is None:
            continue
        if kaynaklar.get(pid) is not None:
            continue
        if _kaynak_id_mi(anahtar):
            kayit_yok_kaynakid.append((pid, anahtar))
        else:
            yetim.append((pid, anahtar))
    return yetim, kayit_yok_kaynakid


def _kaynaklari_oku():
    """Kaynak haritasini okur; yoksa/bozuksa None (FAIL-CLOSED icin ayri edici)."""
    try:
        with open(KAYNAK, encoding="utf-8") as f:
            k = json.load(f)
    except (OSError, ValueError):
        return None
    return k if isinstance(k, dict) else None


# ─────────────────────────────────────────────────────────────── self-test (uydurma fikstur)
def _oz_sinama():
    """Uydurma fiksturde siniflandirici + tarama dogrulugu. GIZLILIK: fiksturde GERCEK
    tedarikci/tasarimci/urun adi YOKTUR — tumu uydurmadir."""
    print("yetim-kayit-kapisi — KENDINI-TEST (uydurma fikstur, canli veri OKUNMAZ)")
    # A1 — r2_anahtar.ONEKLER deger kumesi ile beklenti capasi ayrismamis (onek kaymasi yanar)
    fiili_onekler = set(r2k.ONEKLER.values())
    beklenen_onekler = set(BEKLENEN_ONEKLER_DEGERLERI)
    sonuc("A1", "r2_anahtar.ONEKLER degerleri kanonik 5 onekle birebir", fiili_onekler == beklenen_onekler,
          "fiili=%s (beklenen %s)" % (sorted(fiili_onekler), sorted(beklenen_onekler)))

    # B1 — siniflandirici POZITIF/NEGATIF kontrol (tek kopya, ayri kimlik)
    fikstur = [("th123456", True), ("pr1", True), ("mw998877", True), ("cgt6267929", True),
               ("cgt-6267929", True), ("c3dbazi-slug", True), ("c3d123456", True),
               ("c3d", False),
               ("mercedes-w247-airbag-kapagi-a2476920700", False),
               ("ornek-parca", False), ("x123", False), ("", False)]
    yanlislar = ["%s=>%s(beklenen %s)" % (k, _kaynak_id_mi(k), b)
                 for k, b in fikstur if _kaynak_id_mi(k) != b]
    sonuc("B1", "kaynak-id siniflandiricisi fiksturde dogru (%d girdi)" % len(fikstur),
          not yanlislar, ", ".join(yanlislar))

    # B2 — tarama fiksturu: yetim yakalanir, kaynak-id gecer, parametrik dislanir, kayitli gecer
    CDN = "https://media.pruvo3d.com/urunler"
    kaynaklar = {}
    urunler = [
        {"id": "yetim-1", "gorseller": ["%s/yetim-1-1.jpg" % CDN]},                    # yakalanmali
        {"id": "yetim-2", "gorseller": ["%s/yetim-2-1.jpg" % CDN]},                    # yakalanmali
        {"id": "kaynakid-1", "gorseller": ["%s/th123456-1.jpg" % CDN]},                # gecmeli
        {"id": "parametrik-1", "parametrik": True, "gorseller": ["%s/parametrik-1-1.jpg" % CDN]},  # dislanmali
        {"id": "kayitli-1", "gorseller": ["%s/kayitli-1-1.jpg" % CDN]},                # kayit VAR -> gecmeli
        {"id": "gorselsiz-1", "gorseller": []},                                        # anahtar yok -> dislanmali
    ]
    kaynaklar["kayitli-1"] = {"kaynak": "uydurma", "tur": "uydurma"}
    yetim, kaynakid = _tara(urunler, kaynaklar)
    beklenen_yetim = {"yetim-1", "yetim-2"}
    fiili_yetim = {p for p, _a in yetim}
    beklenen_kaynakid = {"kaynakid-1"}
    fiili_kaynakid = {p for p, _a in kaynakid}
    ok_yetim = fiili_yetim == beklenen_yetim
    ok_kaynakid = fiili_kaynakid == beklenen_kaynakid
    sonuc("B2", "tarama fiksturu: yetim yakalanir + kaynak-id/parametrik/kayitli gecer",
          ok_yetim and ok_kaynakid,
          "yetim=%s (beklenen %s) | kayit-yok-kaynak-id=%s (beklenen %s)"
          % (sorted(fiili_yetim), sorted(beklenen_yetim),
             sorted(fiili_kaynakid), sorted(beklenen_kaynakid)))

    # B3 — kaynak dosyasi OKUNAMADIGINDA fail-closed (None dondurur, sessiz yesil YOK)
    sonuc("B3", "kaynak dosyasi okunamadiginda _tara None dondurur (fail-closed)",
          _tara(urunler, None) == (None, None))

    print("")
    _toplam = len(_iddialar)
    _taban_dustu = _toplam < IDDIA_TABANI
    print("IDDIA: %d (taban %d)%s" % (_toplam, IDDIA_TABANI,
                                      "  🔴 TABAN ALTI" if _taban_dustu else ""))
    print("KIRMIZI_IDDIALAR: %s" % (",".join(hatalar) if hatalar else "-"))
    print("SONUC: %s" % ("KIRMIZI" if (hatalar or _taban_dustu) else "YESIL"))
    return 1 if (hatalar or _taban_dustu) else 0


# ─────────────────────────────────────────────────────────────── canli tarama
def _canli_tarama():
    print("yetim-kayit-kapisi — kaynak kaydi olmayan + baslik-turevi R2 anahtari kapisi")
    if not os.path.exists(URUNLER):
        print("OLCULEMEDI — katalog yok (FAIL-CLOSED): %s" % URUNLER)
        return 2
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
    except (OSError, ValueError):
        print("OLCULEMEDI — katalog okunamadi (FAIL-CLOSED): %s" % URUNLER)
        return 2
    kaynaklar = _kaynaklari_oku()
    if kaynaklar is None:
        print("OLCULEMEDI — kaynak dosyasi okunamadi/bozuk (FAIL-CLOSED): %s" % KAYNAK)
        return 2

    # A1 siniflandirici capasi canli taramada da kosar (kanonik onek kaymasi her ortamda yanar)
    fiili_onekler = set(r2k.ONEKLER.values())
    beklenen_onekler = set(BEKLENEN_ONEKLER_DEGERLERI)
    sonuc("A1", "r2_anahtar.ONEKLER degerleri kanonik 5 onekle birebir",
          fiili_onekler == beklenen_onekler,
          "fiili=%s (beklenen %s)" % (sorted(fiili_onekler), sorted(beklenen_onekler)))

    # B1 siniflandirici kontrolu (A1'den bagimsiz; regex korlesirse tarama bosalir)
    fikstur = [("th123456", True), ("cgt-6267929", True), ("c3dbazi-slug", True),
               ("mercedes-w247-airbag-kapagi-a2476920700", False), ("", False)]
    yanlislar = ["%s=>%s" % (k, _kaynak_id_mi(k)) for k, b in fikstur
                 if _kaynak_id_mi(k) != b]
    sonuc("B1", "kaynak-id siniflandiricisi fiksturde dogru (%d girdi)" % len(fikstur),
          not yanlislar, ", ".join(yanlislar))

    yetim, kayit_yok_kaynakid = _tara(urunler, kaynaklar)
    kayit_sayisi = len(urunler)
    yuzey_ok = kayit_sayisi >= TARAMA_TABANI_KAYIT
    sonuc("C1", "tarama yuzeyi tabanin ustunde (kayit>=%d)" % TARAMA_TABANI_KAYIT, yuzey_ok,
          "taranan kayit=%d" % kayit_sayisi)

    sonuc("C2", "baslik-turevi anahtarli YETIM yok (kayit-YOK + kaynak-id degil + non-parametrik)",
          not yetim,
          ("%d YETIM: %s" % (len(yetim), "; ".join("%s->%s" % (p, a) for p, a in yetim[:12])))
          if yetim else "0 yetim")

    # C3 — ayri sinif (kayit-YOK ama kaynak-id anahtar; catisma riski YOK, hijyen eksigi).
    # KIRMIZI YANMAZ, yalniz RAPORLANIR (kapi kendi sinifini asmaz).
    sonuc("C3", "kayit-YOK + kaynak-id anahtarli urun AYRI siniftir (rapor, blok degil)", True,
          "%d adet (catisma riski yok; hijyen eksigi MaCiT duzlemidir)"
          % len(kayit_yok_kaynakid))

    print("")
    print("OLCUM: TARANAN_KAYIT=%d (taban %d) · YETIM=%d · KAYIT_YOK_KAYNAK_ID=%d"
          % (kayit_sayisi, TARAMA_TABANI_KAYIT, len(yetim), len(kayit_yok_kaynakid)))
    _toplam = len(_iddialar)
    _taban_dustu = _toplam < IDDIA_TABANI
    print("IDDIA: %d (taban %d)%s" % (_toplam, IDDIA_TABANI,
                                      "  🔴 TABAN ALTI" if _taban_dustu else ""))
    print("KIRMIZI_IDDIALAR: %s" % (",".join(hatalar) if hatalar else "-"))
    print("SONUC: %s — gecen %d · kalan %d"
          % ("KIRMIZI" if (hatalar or _taban_dustu) else "YESIL",
             _toplam - len(hatalar), len(hatalar)))
    if hatalar or _taban_dustu:
        return 1
    return 0


def main():
    if "--kendini-test" in sys.argv:
        return _oz_sinama()
    return _canli_tarama()


if __name__ == "__main__":
    sys.exit(main())
