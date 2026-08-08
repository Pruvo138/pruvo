#!/usr/bin/env python3
"""MARKA x PLATFORM kapsama defteri — "hangi markayi hangi sayfada aradik/ekledik".

Amac (Okan, 2026-07-18): marka aramasi TUM platformlarda esitlensin; bir markayi bir
sayfada arayip digerinde unutmayalim. Her ekleme partisi buraya bir kayit dusurur;
rapor hangi (marka,platform) ikilisinin EKSIK oldugunu gosterir.

Kalici defter: /Users/okan/dev/pruvo/.marka-kapsama.json  (gitignore + yedekle --sirlar).

Kullanim:
  python3 tools/marka-kapsama.py                       # matris + eksik (gap) raporu
  python3 tools/marka-kapsama.py --marka Dacia         # tek markanin platform durumu
  python3 tools/marka-kapsama.py kaydet --marka Dacia --platform Printables \
          --taranan 83 --eklenen 57 --elenen 26        # parti sonrasi kayit (ekleme akisi cagirir)
  python3 tools/marka-kapsama.py --backfill            # .urun-kaynaklari.json'dan BOS hucreleri doldur
  python3 tools/marka-kapsama.py --backfill --kuru-prova       # hicbir sey yazma, ne olacagini bas
  python3 tools/marka-kapsama.py --backfill --ezmeye-izin-ver  # ACIK istekle mevcut sayimi EZ (yikici)

🔴 --backfill FAIL-CLOSED (8 Agu): mevcut bir hucre degerini KUCULTEMEZ / sessizce EZEMEZ.
Eski surum `kayit["eklenen"] = cnt` ile SET ediyordu; olculdu: bugunku defterde 101
non-null hucreyi ezecek, bir kismini KUCULTECEKTI (190 -> 183 gibi) — geri gelmeyen
hasat muhasebesi kaybi. Artik yalniz BOS (None) hucre doldurulur, catisan hucre
YAZILMAZ, tek tek raporlanir ve cikis kodu KOD_CATISMA olur. Bilerek ezmek ACIK
`--ezmeye-izin-ver` bayragi ISTER (varsayilanda KAPALI).

BIRIM = KANONIK PANEL HUCRESI (marka_katla.hucre_deger), ham dict anahtari DEGIL:
`{"eklenen": 0, "taranan": 0}` kaydi ham anahtar olarak VARDIR ama hucre olarak None'dir;
ve bir hucreye birden fazla ham anahtar katkida bulunabilir ("Toyota" + "Toyota Corolla").
Karar bu yuzden kanonik hucre uzerinden verilir — ham anahtara bakan kontrol dolu bir
hucreyi "bos" sanip uzerine EKLER ve sayimi sisirir.

Kabul testi: tools/backfill-koruma-test.py · mutasyon: tools/backfill-mutasyon-test.py
"""
import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marka_katla as mk  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Yollar ortam degiskeniyle EZILEBILIR — kabul testi/mutasyon bataryasi SENTETIK fikstur
# uzerinde kosabilsin diye (canli defter gitignore'da ve CI'da YOKTUR; test onu OKUMAZ).
DEFTER = os.environ.get("PRUVO_KAPSAMA_DEFTER") or os.path.join(KOK, ".marka-kapsama.json")
KAYNAK = os.environ.get("PRUVO_KAPSAMA_KAYNAK") or os.path.join(KOK, ".urun-kaynaklari.json")
URUNLER = os.environ.get("PRUVO_KAPSAMA_URUNLER") or os.path.join(KOK, "urunler.json")

KOD_CATISMA = 3   # cozulmemis catisma var (fail-closed: sessiz basari YOK)

# 🔴 ELLE LISTE YAZMA — tek kanonik tanim marka_katla.PLATFORM_TANIMI
# (defter YAZICISI ile panel OKUYUCUSU ayni kumeyi gormezse: yazici bilinmeyen platform
# uyarisi basar ama kaydeder, panel o kolonu HIC gostermez -> sessiz kor nokta.)
PLATFORMLAR = mk.PLATFORMLAR
DOMAIN = dict(mk.PLATFORM_DOMAIN)


def _yukle(path, bos):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return bos
    return bos


def _defter_oku():
    return _yukle(DEFTER, {})


def _defter_yaz(d):
    with open(DEFTER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)


def _platform_link(link):
    l = (link or "").lower()
    for dom, ad in DOMAIN.items():
        if dom in l:
            return ad
    return None


def kaydet(marka, platform, taranan, eklenen, elenen, tarih=None):
    if platform not in PLATFORMLAR:
        # esnek: bilinen adlarla eslesmezse yine kaydet ama uyar
        print("UYARI: bilinmeyen platform '%s' (yine de kaydediliyor)" % platform)
    # FLOCK: paralel backfill'ler ayni anda kaydet cagirinca birbirinin ledger yazimini
    # EZMESIN (read-modify-write atomik olmali; defter flock'suzdu -> kayit kaybi riski).
    with open(DEFTER + ".lock", "w") as _lk:
        fcntl.flock(_lk, fcntl.LOCK_EX)
        d = _defter_oku()
        m = d.setdefault(marka, {})
        kayit = m.get(platform, {"taranan": 0, "eklenen": 0, "elenen": 0, "parti": 0})
        kayit["taranan"] = max(kayit.get("taranan", 0), int(taranan or 0))
        kayit["eklenen"] = kayit.get("eklenen", 0) + int(eklenen or 0)
        kayit["elenen"] = kayit.get("elenen", 0) + int(elenen or 0)
        kayit["parti"] = kayit.get("parti", 0) + 1
        kayit["son_tarih"] = tarih or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        m[platform] = kayit
        _defter_yaz(d)
    print("kaydedildi: %s / %s -> taranan=%s eklenen(+%s) elenen(+%s)" %
          (marka, platform, kayit["taranan"], eklenen, elenen))


def _turet(kayn, urun):
    """(kanonik marka -> platform -> urun sayisi, eslesen_urun_sayisi).

    BIRIM KANONIK: ham marka degeri mk.kanonik_veya_none ile katlanir; taninmayan
    (tasarimci-adi/model-kodu) deger SAYILMAZ — panel satiri da yoktur.
    Bir urun marka[] listesinde birden fazla taninmis marka tasiyabilir (BMW + Mini);
    o urun HER IKI markanin kapsamina sayilir, ama ayni marka icin IKI KEZ sayilmaz."""
    turetilen = {}
    eslesen = 0
    for uid, k in kayn.items():
        if isinstance(k, dict):
            link = k.get("link") or k.get("kaynak") or k.get("url") or ""
        elif isinstance(k, str):
            link = k
        else:
            continue
        plat = _platform_link(link)
        p = urun.get(uid)
        if not plat or not p:
            continue
        gorulen = set()
        for ham in (p.get("marka") or []):
            kan = mk.kanonik_veya_none(ham)
            if kan is None or kan in gorulen:
                continue
            gorulen.add(kan)
            turetilen.setdefault(kan, {}).setdefault(plat, 0)
            turetilen[kan][plat] += 1
        if gorulen:
            eslesen += 1
    return turetilen, eslesen


def _kanonik_hucreler(defter):
    """kanonik marka -> platform -> HUCRE degeri (int | None). Karar birimi budur."""
    agg = mk.kanonik_kapsama(defter)
    return {m: {p: mk.hucre_deger(pl.get(p)) for p in PLATFORMLAR}
            for m, pl in agg.items()}


def _hucreye_yaz(d, marka, plat, hedef, ez=False):
    """Kanonik HUCRE degerini tam olarak `hedef` yapacak sekilde deftere yazar.

    ez=False: yalniz hucre BOS (None) iken cagrilir -> tum katkilar zaten 0, kanonik
              anahtara `hedef` yazmak hucreyi tam olarak `hedef` yapar.
    ez=True : YIKICI. Ayni kanonik markaya katlanan DIGER ham anahtarlarin bu
              platformdaki `eklenen` katkisi SIFIRLANIR, yoksa hucre hedefin uzerinde
              kalirdi. Yalnizca --ezmeye-izin-ver ile calisir."""
    if ez:
        for ham, plats in d.items():
            if ham == marka or not isinstance(plats, dict):
                continue
            if mk.kanonik_veya_none(ham) != marka:
                continue
            k = plats.get(plat)
            if isinstance(k, dict):
                k["eklenen"] = 0
    m = d.setdefault(marka, {})
    kayit = m.get(plat)
    if not isinstance(kayit, dict):
        kayit = {"taranan": 0, "eklenen": 0, "elenen": 0, "parti": 0}
    kayit["eklenen"] = int(hedef)
    kayit.setdefault("son_tarih", "backfill")
    m[plat] = kayit


def backfill(ezmeye_izin_ver=False, kuru_prova=False):
    """Eklenen urunlerden (kaynak link -> platform, urunler.json -> marka) BOS kapsama
    hucrelerini doldur. Cikis kodu doner (0 = temiz, KOD_CATISMA = cozulmemis catisma).

    FAIL-CLOSED: mevcut bir hucre degeri ASLA sessizce ezilmez/kucultulmez. Uc hal:
      hucre None            -> DOLDUR (turetilen > 0 ise; 0 icin "arandi-bos" UYDURULMAZ)
      hucre == turetilen    -> NO-OP (idempotent)
      hucre != turetilen    -> CATISMA: yazma, eski->yeni raporla, KOD_CATISMA ile cik
                               (--ezmeye-izin-ver verilmisse BILEREK uzerine yaz)"""
    kayn = _yukle(KAYNAK, {})
    urun = {p["id"]: p for p in _yukle(URUNLER, [])}
    turetilen, eslesen = _turet(kayn, urun)

    # FLOCK: paralel yazicilar read-modify-write'i bolmesin; defter kilit ALTINDA
    # YENIDEN OKUNUR (baska oturum bu arada yazmis olabilir), yazim TEK atomik islem.
    with open(DEFTER + ".lock", "w") as _lk:
        fcntl.flock(_lk, fcntl.LOCK_EX)
        d = _defter_oku()
        hucre = _kanonik_hucreler(d)
        doldur = []
        catisma = []
        for marka in sorted(turetilen):
            for plat in sorted(turetilen[marka]):
                cnt = int(turetilen[marka][plat])
                if cnt <= 0:
                    continue
                mevcut = hucre.get(marka, {}).get(plat)
                if mevcut is None:
                    doldur.append((marka, plat, cnt))
                elif int(mevcut) == cnt:
                    continue
                else:
                    catisma.append((marka, plat, int(mevcut), cnt))
        yazilan = 0
        ezilen = 0
        if not kuru_prova:
            for marka, plat, cnt in doldur:
                _hucreye_yaz(d, marka, plat, cnt)
                yazilan += 1
            if ezmeye_izin_ver:
                for marka, plat, _eski, cnt in catisma:
                    _hucreye_yaz(d, marka, plat, cnt, ez=True)
                    ezilen += 1
            if yazilan or ezilen:
                _defter_yaz(d)

    print("backfill%s: %d urun eslesti, %d marka x platform turetildi"
          % (" (KURU PROVA — yazilmadi)" if kuru_prova else "", eslesen,
             sum(len(v) for v in turetilen.values())))
    print("DOLDURULAN (hucre None -> sayi) : %d" % yazilan)
    print("EZILEN (--ezmeye-izin-ver ile)  : %d" % ezilen)
    print("CATISMA (hucre != turetilen)    : %d" % len(catisma))
    for marka, plat, eski, yeni in catisma:
        print("  CATISMA %s / %s : mevcut %d -> turetilen %d%s%s"
              % (marka, plat, eski, yeni,
                 "  (KUCULTME)" if yeni < eski else "",
                 "  [EZILDI]" if (ezilen and not kuru_prova) else "  [YAZILMADI]"))
    for marka, plat, cnt in doldur[:200]:
        print("  DOLDU   %s / %s : None -> %d%s"
              % (marka, plat, cnt, " (kuru prova)" if kuru_prova else ""))
    if catisma and not (ezmeye_izin_ver and not kuru_prova):
        print("SONUC: CATISMA VAR — %d hucre KORUNDU (yazilmadi). Bilerek ezmek icin: "
              "--ezmeye-izin-ver" % len(catisma))
        return KOD_CATISMA
    print("SONUC: TEMIZ")
    return 0


def rapor(tek_marka=None):
    raw = _defter_oku()
    if not raw:
        print("defter bos. once: python3 tools/marka-kapsama.py --backfill")
        return
    # Rapor satır evreni = KANONIK TANINMIS_MARKALAR; ham anahtarlar markaKatla ile
    # kanonik markaya katlanır (Toyota cover... -> Toyota), çöp anahtar HİÇ görünmez.
    d = mk.kanonik_kapsama(raw)
    markalar = [mk.markaKatla(tek_marka)] if tek_marka else sorted(d.keys())
    bas = "MARKA".ljust(24) + "".join(p[:4].ljust(7) for p in PLATFORMLAR) + " EKSIK"
    print(bas)
    print("-" * len(bas))
    for marka in markalar:
        m = d.get(marka, {})
        hucre = ""
        eksik = []
        for p in PLATFORMLAR:
            k = m.get(p)
            if k and (k.get("eklenen", 0) > 0 or k.get("taranan", 0) > 0):
                hucre += (str(k.get("eklenen", 0))).ljust(7)
            else:
                hucre += "·".ljust(7)
                eksik.append(p)
        print(marka.ljust(24) + hucre + " " + (",".join(e[:4] for e in eksik) if eksik else "—"))
    print("\n(hucre = eklenen sayisi; · = o platformda aranmamis/urun yok; EKSIK = parity acigi)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="komut")
    k = sub.add_parser("kaydet")
    k.add_argument("--marka", required=True)
    k.add_argument("--platform", required=True)
    k.add_argument("--taranan", type=int, default=0)
    k.add_argument("--eklenen", type=int, default=0)
    k.add_argument("--elenen", type=int, default=0)
    k.add_argument("--tarih", default=None)
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_true",
                    help="YIKICI: mevcut hucre degerlerini turetilenle EZ (varsayilan KAPALI)")
    ap.add_argument("--kuru-prova", dest="kuru_prova", action="store_true",
                    help="hicbir sey yazma, ne olacagini bas")
    ap.add_argument("--marka", dest="rapor_marka", default=None)
    a = ap.parse_args()
    if a.komut == "kaydet":
        kaydet(a.marka, a.platform, a.taranan, a.eklenen, a.elenen, a.tarih)
    elif a.backfill:
        sys.exit(backfill(a.ezmeye_izin_ver, a.kuru_prova))
    elif a.ezmeye_izin_ver or a.kuru_prova:
        # sessizce yok sayma: kullanici ezme/prova istedigini sanip rapor almasin
        print("HATA: --ezmeye-izin-ver / --kuru-prova yalniz --backfill ile anlamlidir")
        sys.exit(2)
    else:
        rapor(a.rapor_marka)
