#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO SIPARIS LISTESI — canli D1'den siparisleri okur. SALT-OKUNUR.

    python3 tools/siparisler.py                       # son 10, tum durumlar (MASKELI)
    python3 tools/siparisler.py --son 25
    python3 tools/siparisler.py --durum odendi
    python3 tools/siparisler.py --son 5 --durum bekliyor
    python3 tools/siparisler.py --acik                # ham ad/tel — YALNIZ terminalde

KAPSAM = SADECE OKUMA. wrangler'a giden tek yol `wrangler_sorgu()`; SELECT
disinda bir ifade gecerse (assert) calismadan durur. Hicbir yazma/silme yolu
YOKTUR — shop/ worker'i (src/index.js) siparisleri yazar, bu arac dokunmaz.

KISISEL VERI — TEK KURAL (KANAL EKSENI): TTY DISINA (boru, `>` yonlendirme,
`2>&1`, capture_output, CI) HAM MUSTERI VERISI ve MUSTERI SERBEST METNI CIKMAZ;
stdout da stderr de dahil. Uc uygulama noktasi:
  1. `musteri_ad` / `musteri_tel` VARSAYILAN MASKELI (`maskele_ad`/`maskele_tel`).
     `--acik` bayragi ham basar ama FAIL-CLOSED'dir: yalniz `_tty()` True iken
     etkilidir; degilse SESSIZCE YUTULMAZ — maskeli basar + stderr'e tek satir uyari.
  2. `parametre_detay` (musterinin yazdigi serbest metin) maskelenemez -> TTY
     disinda HIC BASILMAZ, yerine karakter sayisi yer tutucusu konur. Olcut TTY'dir,
     `--acik` DEGIL.
  3. `wrangler_sorgu` hata yollarinda kapi KANALA GORE AYRIK (`_ham_dokum`):
     wrangler STDOUT'u (= SELECT sonucunun ham JSON'u) yalniz TTY'de basilir;
     wrangler STDERR'i (= hata metni, sorgu sonucu tasimaz) HER KOSULDA TAM basilir.
     Teshis (hata sinifi + exit kodu + bayt sayilari + stderr) hicbir kolda kaybolmaz.
Nobetci: tools/siparis-maske-test.py.

Sema: tools/d1-sema.sql (tablo: siparisler). Para KURUS tamsayisinda tutulur
(yuvarlama yok); genel toplam = tutar_kurus + kargo_kurus (KDV dahil fiyat,
kdv_kurus sadece dokum icin — bkz sema yorumu).

wrangler'i shop/ dizininden cagiriyoruz (wrangler.toml + D1 binding orada,
KURULUM.md'deki gibi); yerelde wrangler'in kendi oturumu kullanilir, token
gerekmez (bkz tools/d1-sync.py'deki ayni desen).
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    YEREL_TZ = ZoneInfo("Europe/Istanbul")
except Exception:  # pragma: no cover - zoneinfo veritabani eksikse yedek
    YEREL_TZ = timezone(timedelta(hours=3))

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
DB = "pruvo-katalog"

UYARI_ACIK_YOKSAYILDI = (
    "--acik yoksayildi: cikti terminal degil (boru/log/CI) — maskeli basildi")

DURUMLAR = ("odendi", "bekliyor", "havale-bekliyor", "incele")
KOLONLAR = (
    "siparis_no", "tarih", "durum", "odeme_yontemi",
    "tutar_kurus", "kargo_kurus", "kdv_kurus",
    "musteri_ad", "musteri_tel", "urunler",
)


# ------------------------------------------------------------------ sorgu

def sql_sorgu(son, durum):
    """SELECT SQL'i uretir. `durum` "hepsi" ise filtre eklenmez.

    `durum` argparse `choices` ile zaten kisitli (DURUMLAR + "hepsi"); yine de
    burada ikinci kez dogrulaniyor — bu fonksiyon dogrudan da cagrilabilir.
    """
    if durum != "hepsi" and durum not in DURUMLAR:
        raise ValueError("bilinmeyen durum: %r" % durum)
    son = max(int(son), 0)
    sql = "SELECT %s FROM siparisler" % ", ".join(KOLONLAR)
    if durum != "hepsi":
        sql += " WHERE durum = '%s'" % durum
    sql += " ORDER BY id DESC LIMIT %d" % son
    return sql


YER_TUTUCU_STDOUT = (
    "  wrangler STDOUT'u SELECT SONUCUDUR (musteri_ad/musteri_tel icerir) —\n"
    "  yalnizca GERCEK TERMINALDE basilir; bu kosum boru/dosya/CI'ya akiyor.")


def _ham_dokum(baslik, p):
    """Hata metnini uretir. KAPI KANALA GORE AYRIKTIR — stdout kapali, stderr acik.

    🔴 NEDEN AYRIK (31 Tem, ucuncu tur — olculdu):
      * `p.stdout` = `wrangler d1 execute --json` ciktisi, yani SELECT SONUCUNUN HAM
        JSON'u; `musteri_ad`/`musteri_tel` AYNEN icindedir -> TTY disina CIKMAZ.
      * `p.stderr` = wrangler'in HATA METNI ("no such table: siparisler [code: 7502]",
        "getaddrinfo ENOTFOUND", JSON ayristirma hatasi). SORGU SONUCU TASIMAZ ->
        HER KOSULDA TAM basilir. Ikisi `ham = stdout + stderr` diye tek parca sayilinca
        TESHIS OLUYORDU: `stdout=0 bayt` olan, yani sonuc icermesi IMKANSIZ olan yolda
        bile hata metni bastiriliyordu ve CI'da teshis "exit kodu + bayt sayisi"na
        iniyordu. Bu yetersizligin "dogal" cozumu ise taniya `ham[:N]` eklemek olur —
        yani kanalin kapiyi sokmeden yeniden acilmasi. Ayrim tam da bunu onler.

    TESHIS HER KOSULDA: hata sinifi (baslik), wrangler exit kodu, stdout/stderr bayt
    sayilari ve STDERR'IN TAM METNI. Terminale sakli tutulan tek sey stdout govdesidir.
    ("cikti vermedi" yolunda stdout'ta '[' yoktur — sonuc icermesi imkansizdir — ama
    yine ayni kapidan gecer ki wrangler ciktisi degisirse kanal sessizce acilmasin.)
    """
    cikti = p.stdout or ""
    hata = p.stderr or ""
    tani = ("%s\n  tani: wrangler exit=%s · stdout=%d bayt · stderr=%d bayt"
            % (baslik, p.returncode, len(cikti), len(hata)))
    parcalar = [tani]
    if hata.strip():
        parcalar.append("  wrangler stderr (TESHIS — sorgu sonucu tasimaz, HER KOSULDA):")
        parcalar.append(hata[-2000:])
    if cikti.strip():
        if _tty():
            parcalar.append("  wrangler stdout (SELECT sonucu — HAM):")
            parcalar.append(cikti[-2000:])
        else:
            parcalar.append(YER_TUTUCU_STDOUT)
    return "\n".join(parcalar)


def wrangler_sorgu(sql):
    """wrangler d1 execute --remote --json calistirir, satir listesi doner.

    SALT-OKUNUR KAPI: SELECT disinda bir ifade buraya gelirse calismaz.
    Hata yollarindaki ham dokum `_ham_dokum()` kanal kapisindan gecer.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("sadece SELECT calistirilir, gelen: %r" % sql)

    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB,
             "--remote", "--json", "--command", sql]
    p = subprocess.run(komut, cwd=SHOP, capture_output=True, text=True)
    # `ham` YALNIZ kimlik-hatasi TESPITI icindir (iki kanalda da gorunebilir); DOKUM
    # icin KULLANILMAZ — dokum kanal kanal ayrilir, bkz _ham_dokum().
    ham = (p.stdout or "") + (p.stderr or "")

    if "code: 10000" in ham or "Authentication error" in ham:
        sys.exit(
            "D1 KIMLIK HATASI (code 10000) — token/oturum D1'e erisemiyor.\n"
            "  Yerelde 'npx wrangler login' ile giris yapilmis olmali (tools/d1-sync.py\n"
            "  ile ayni gereksinim)."
        )

    i = p.stdout.find("[")
    if i == -1:
        sys.exit(_ham_dokum("wrangler cikti vermedi:", p))
    try:
        veri = json.loads(p.stdout[i:])
    except (ValueError, TypeError):
        sys.exit(_ham_dokum("wrangler ciktisi cozulemedi:", p))

    if not veri or not veri[0].get("success", False):
        sys.exit(_ham_dokum("wrangler sorgusu basarisiz:", p))
    return veri[0].get("results", []) or []


# ------------------------------------------------------------------ bicim

def tl(kurus):
    """Kurus tamsayisini Turkce bicimli 'X.XXX,XX TL' string'e cevirir."""
    try:
        lira = (kurus or 0) / 100.0
    except TypeError:
        lira = 0.0
    s = "{:,.2f}".format(lira)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " TL"


def yerel_saat(iso_utc):
    """ISO 8601 UTC ('...Z') -> 'gg.aa.yyyy ss:dd' Europe/Istanbul saatinde.

    Format bozuksa (beklenmedik veri) crash etmez, ham degeri geri verir —
    bu arac SALT-OKUNUR bir rapor araci, kotu bir satir yuzunden durmamali.
    """
    if not iso_utc:
        return "?"
    s = iso_utc[:-1] + "+00:00" if iso_utc.endswith("Z") else iso_utc
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return iso_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(YEREL_TZ).strftime("%d.%m.%Y %H:%M")


def maskele_ad(ad):
    """Musteri adini maskeler: her kelimenin ILK harfi + '***'.

    "Test Musteri" -> "T*** M***" · "Ayse" -> "A***" · bos/None -> "-".
    SAF fonksiyon (nobetci birim olarak surer).
    """
    ad = (ad or "").strip()
    if not ad:
        return "-"
    return " ".join(k[0] + "***" for k in ad.split())


def maskele_tel(tel):
    """Telefonu maskeler: SON 4 karakter acik, oncesindeki HER karakter '*'.

    "5551112233" -> "******2233" · "+905551112233" -> "*********2233"
    4 karakterden kisa -> tamami '*' · bos/None -> "-".
    SAF fonksiyon (nobetci birim olarak surer).
    """
    tel = (tel or "").strip()
    if not tel:
        return "-"
    if len(tel) < 4:
        return "*" * len(tel)
    return "*" * (len(tel) - 4) + tel[-4:]


def _tty():
    """stdout GERCEK terminal mi. Ayri fonksiyon: nobetci bunu monkeypatch'ler
    (siparisler.py'ye test-ozel arka kapi/env fikstur EKLENMEZ)."""
    return sys.stdout.isatty()


def _kisalt(metin, azami=60):
    metin = (metin or "").strip()
    if len(metin) <= azami:
        return metin
    return metin[:azami - 3] + "..."


def format_siparis(row, acik=False):
    """Tek siparis satirini okunur cok-satirli bloga cevirir.

    `acik` VARSAYILAN False -> musteri ad/tel MASKELI basilir. True yalnizca
    main()'in TTY kapisindan gecen `--acik` kolundan gelir.
    """
    lines = []
    lines.append("=" * 66)
    lines.append("%s   %s (yerel)" % (row.get("siparis_no") or "?",
                                       yerel_saat(row.get("tarih"))))
    lines.append("durum: %-16s yontem: %s"
                  % (row.get("durum") or "?", row.get("odeme_yontemi") or "?"))

    tutar = row.get("tutar_kurus") or 0
    kargo = row.get("kargo_kurus") or 0
    genel = tutar + kargo
    lines.append("urun toplami: %s | kargo: %s | genel toplam: %s"
                  % (tl(tutar), tl(kargo), tl(genel)))

    ham_ad = row.get("musteri_ad") or ""
    ham_tel = row.get("musteri_tel") or ""
    if acik:
        gosterilecek_ad = ham_ad.strip() or "-"
        gosterilecek_tel = ham_tel.strip() or "-"
    else:
        gosterilecek_ad = maskele_ad(ham_ad)
        gosterilecek_tel = maskele_tel(ham_tel)
    lines.append("musteri: %s | %s" % (gosterilecek_ad, gosterilecek_tel))
    lines.append("-" * 66)

    try:
        kalemler = json.loads(row.get("urunler") or "[]")
    except (ValueError, TypeError):
        kalemler = []
    if not isinstance(kalemler, list) or not kalemler:
        lines.append("  (urun satiri yok)")
    else:
        for k in kalemler:
            if not isinstance(k, dict):
                continue
            baslik = k.get("baslik") or k.get("id") or "?"
            mr = " / ".join(p for p in (k.get("malzeme"), k.get("renk")) if p)
            lines.append("  - %s" % baslik)
            lines.append("      %s | adet: %s | tutar: %s"
                          % (mr or "-", k.get("adet", "?"),
                             tl(k.get("tutar_kurus") or 0)))
            # 🔴 KANAL KAPISI — `parametre_detay` MUSTERININ YAZDIGI SERBEST METINDIR
            # (isim kazima, ozel yazi): icinde ad/telefon olabilir ve MASKELENEMEZ
            # (hangi parcanin PII oldugu bilinemez). Olculdu: detaya konmus ad+telefon
            # VARSAYILAN (maskeli) kosumda aynen basiliyordu. Cozum alan degil KANAL:
            # TTY disina (boru/yonlendirme/CI) CIKMAZ; terminalde bugunku gibi
            # kisaltilmis basar (Okan'in uretim icin ihtiyaci var). Olcut TTY'dir,
            # `--acik` DEGIL — bayrak bu alani acmaz.
            # `baslik` BILEREK burada DEGIL: o KATALOG verisidir (urunler.json'dan
            # gelir, musteri metni degildir) -> maskelenmez, gizlenmez.
            ham_detay = (k.get("parametre_detay") or "").strip()
            if ham_detay:
                if _tty():
                    lines.append("      %s" % _kisalt(ham_detay))
                else:
                    lines.append("      (parametre detayi: %d karakter — terminalde "
                                 "gorunur)" % len(ham_detay))
    return "\n".join(lines)


# ------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--son", type=int, default=10, help="son N siparis (varsayilan 10)")
    ap.add_argument("--durum", choices=list(DURUMLAR) + ["hepsi"], default="hepsi")
    ap.add_argument("--acik", action="store_true",
                    help="musteri ad/telefonunu HAM bas — YALNIZ gercek terminalde "
                         "etkili, boru/dosya/CI'da yoksayilir")
    args = ap.parse_args(argv)

    # FAIL-CLOSED: acik cikti asla loglanabilir bir kanala akmaz.
    acik = False
    if args.acik:
        if _tty():
            acik = True
        else:
            print(UYARI_ACIK_YOKSAYILDI, file=sys.stderr)

    sql = sql_sorgu(args.son, args.durum)
    satirlar = wrangler_sorgu(sql)

    print("=" * 66)
    print("PRUVO SIPARISLER — son %d, durum=%s" % (args.son, args.durum))
    print("=" * 66)
    if not satirlar:
        print("(kayit yok)")
        return 0
    for row in satirlar:
        print(format_siparis(row, acik=acik))
        print()
    print("Toplam: %d siparis" % len(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
