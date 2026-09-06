#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON TURU — `d1-sync-tani-test.py` gercekten OLCUYOR mu?

  python3 tools/d1-sync-tani-mutasyon.py

Her mutant, `tools/d1-sync.py`nin GECICI bir KOPYASINA uygulanir (CANLI govde ASLA
degistirilmez → [[mutant-canli-govdede-yasamaz]]) ve batarya `--govde <kopya>` ile
kosturulur. Kopya sentetik bir kokte (`<tmp>/tools/d1-sync.py`) durur; komsu modul
`konfigur-bundle-kapisi.py` oraya SEMBOLIK BAGLA konur, geri kalan import'lar gercek
`tools/` dizininden cozulur.

UC AYRI SORU, UCU DE OLCULUR (biri eksikse mutasyon turu KENDINI kandirir):
  (1) YAMA TUTTU MU?  — dizge gercekten degisti mi (sayi ile).
  (2) MUTANT HEDEFE ULASTI MI? — sonuc TABANLA AYNI ise mutant hic dokunmamistir
      ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
  (3) HEDEF KOLU MU OLDURDU? — beklenen IDDIA ADLARI dusenler listesinde mi
      (K182: "kirmizi yandi" yetmez, DOGRU kol olmeli).
KONTROL mutantlari davranisi DEGISTIRMEYEN sabit oynamalaridir; batarya onlarda YESIL
kalmali — kalmazsa batarya davranisa degil SABITE capalanmis demektir.
"""
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
GOVDE = os.path.join(BURASI, "d1-sync.py")
BATARYA = os.path.join(BURASI, "d1-sync-tani-test.py")
KOMSU = "konfigur-bundle-kapisi.py"
TUR_TAVANI = 180          # tek mutant kosumu icin sert tavan (sn)

# (ad, eski, yeni, oldurmesi_beklenen_iddia_onekleri)  — bos kume = KONTROL
MUTANTLAR = [
    ("M1 zaman asimi KALDIRILDI",
     "timeout=tavan, env=ort)",
     "env=ort)",
     ("B1", "B2", "B3", "B4", "B6", "B8")),

    ("M2 ISINMIS tavan OLCULEN isinmis maksimumun ALTINA cekildi (120 -> 6)",
     "WRANGLER_TAVAN_SN = 120  ",
     "WRANGLER_TAVAN_SN = 6  ",
     ("B10",)),

    ("M3 ISINMIS TABAN olculen isinmis maksimumun ALTINA cekildi (120 -> 6)",
     "WRANGLER_TAVAN_TABANI = 120  ",
     "WRANGLER_TAVAN_TABANI = 6  ",
     ("B11",)),

    # 🔴 4 Eyl: SOGUK/ISINMIS kol AYRIMI — yeni kollar MUTANTSIZ birakilmaz.
    ("M3b SOGUK tavan olculen soguk maksimumun (307,1sn) ALTINA cekildi (450 -> 100)",
     "WRANGLER_SOGUK_TAVAN_SN = 450",
     "WRANGLER_SOGUK_TAVAN_SN = 100",
     ("B10b",)),

    ("M3c KOL SECIMI CAKILI: cache hep ISINMIS sayilir -> soguk doldurma kosumu\n     DAR tavanla KESILIR (koruma korudugunu durdurur)",
     "    soguk = not npm_cache_isinmis()",
     "    soguk = False",
     ("B10c",)),

    ("M3d KALICI ozel cache DEVRE DISI (paylasilan cache'e geri donus)",
     "    return dict(os.environ, npm_config_cache=NPM_CACHE_DIZINI)",
     "    return dict(os.environ)",
     ("E3",)),

    ("M4 TEK UCUS kilidi hic ALINMIYOR",
     "    if not _YEREL_KILIT_SAHIBI:\n"
     '        kilit = yazici_kilidi_al(bekleme_sn=OKUYUCU_BEKLEME_SN, kol="ARAC")',
     "    if False:\n"
     '        kilit = yazici_kilidi_al(bekleme_sn=OKUYUCU_BEKLEME_SN, kol="ARAC")',
     ("C2", "C3", "C4")),

    ("M5 ARAC kolu BEKLEMIYOR (MESGUL kolu yazici mesajina duser, duyuru YOK)",
     'kilit = yazici_kilidi_al(bekleme_sn=OKUYUCU_BEKLEME_SN, kol="ARAC")',
     'kilit = yazici_kilidi_al(bekleme_sn=0, kol="ARAC")',
     ("C2", "C4")),

    ("M6 `npx` yok kolu SESSIZ (ciplak istisna sizar)",
     "    except FileNotFoundError:\n        sys.exit(npx_yok_metni(komut))",
     "    except FileNotFoundError:\n        raise",
     ("D1", "D2", "D3")),

    ("M7 gecici npm cache SILINMIYOR (disk izi kalir)",
     "            shutil.rmtree(_gecici, ignore_errors=True)",
     "            pass",
     ("E2",)),

    # 🔴 6 Eyl: ENV KOLLARI ARTIK IKI KOLDA olculuyor (B12-*/B13-*/B14-*). O kollari
    #   MUTANTSIZ birakmak, tam da kapatilan arizayi geri davet ederdi: iddia TEK
    #   sabite capalanir, sonuc kosucunun cache haline baglanir, yerelde yesil / CI'da
    #   kirmizi yanar. Asagidaki iki oldurucu SOGUK kolu ADIYLA hedefler ve ISINMIS
    #   kolda YESIL kalir — yani "kol ayrimini" gercekten olcerler.
    ("M8 TABAN DONUSU ISINMIS SABITINE CAKILI (soguk kolda 450 yerine 120 doner —\n"
     "     koruma korudugu SOGUK doldurma kosumunu KESER)",
     "        return taban\n    return istek",
     "        return WRANGLER_TAVAN_TABANI\n    return istek",
     ("B12-SOGUK", "B14b")),

    ("M9 COP ENV ISINMIS VARSAYILANINA CAKILI (soguk kolda 450 yerine 120 doner)",
     "              % (ham, varsayilan), file=sys.stderr)\n        return varsayilan",
     "              % (ham, varsayilan), file=sys.stderr)\n        return WRANGLER_TAVAN_SN",
     ("B14-SOGUK",)),

    # 🔴 6 Eyl — TUTANAK ETIKETI de bir DAVRANISTIR: yanlis etiketlenmis PID,
    #   teshisi olmus bir surece goturur. Bu oldurucu eski (yaniltici) etikete geri
    #   doner; C10 ADIYLA kirmizi yanmali.
    ("M10 MESGUL tutanagi kendi PID'ini SAHIBIN PID'i gibi sunar (`bekleyen PID` "
     "etiketi kaldirildi)",
     '"BEKLENIYOR (tavan=%.0f sn, bekleyen PID=%d, kilit=%s). "',
     '"BEKLENIYOR (tavan=%.0f sn, PID=%d, kilit=%s). "',
     ("C10",)),

    ("M11 MESGUL tutanagi SAHIBIN PID'inin OLCULEMEDIGINI SOYLEMEZ "
     "(turetilemeyeni sessizce gecer)",
     '"Yigina EKLENMEDI. Kilidi TUTANIN PID\'i buradan "\n'
     '                          "olculemez; su komut gosterir:\\n"',
     '"Yigina EKLENMEDI.\\n"',
     ("C11",)),

    # ── KONTROL: davranis DEGISMEZ, batarya YESIL KALMALI ──
    ("KONTROL-1 bekleme 480 -> 500 (davranis notr)",
     "OKUYUCU_BEKLEME_SN = 480.0", "OKUYUCU_BEKLEME_SN = 500.0", ()),
    ("KONTROL-2 kilit yoklama araligi 0.5 -> 0.4 (davranis notr)",
     "_KILIT_YOKLAMA_SN = 0.5", "_KILIT_YOKLAMA_SN = 0.4", ()),
    ("KONTROL-3 ISINMIS tavan 120 -> 200 (hala olculen maksimumun UZERINDE)",
     "WRANGLER_TAVAN_SN = 120  ", "WRANGLER_TAVAN_SN = 200  ", ()),
    # KONTROL-4: SOGUK kol sabiti oynatildi ama HALA olculen soguk maksimumun (307,1)
    # UZERINDE ve ISINMIS kolundan FARKLI -> davranis notr, batarya YESIL kalmali.
    # Kalmazsa yeni B12-/B13-/B14- kollari davranisa degil SABITE capalanmis demektir.
    ("KONTROL-4 SOGUK tavan 450 -> 500 (hala soguk maksimumun UZERINDE)",
     "WRANGLER_SOGUK_TAVAN_SN = 450", "WRANGLER_SOGUK_TAVAN_SN = 500", ()),
]


def bataryayi_kos(govde_yolu):
    """(rc, iddia, gecti, kirmizi, dusenler) dondur."""
    p = subprocess.run([sys.executable, BATARYA, "--govde", govde_yolu],
                       capture_output=True, text=True, timeout=TUR_TAVANI)
    ham = (p.stdout or "") + (p.stderr or "")
    iddia = gecti = kirmizi = None
    dusenler = []
    for satir in ham.splitlines():
        if satir.startswith("IDDIA="):
            parca = dict(x.split("=", 1) for x in satir.split())
            iddia = int(parca["IDDIA"])
            gecti = int(parca["GECTI"])
            kirmizi = int(parca["KIRMIZI"])
        elif satir.startswith("DUSENLER="):
            dusenler = [x.strip() for x in satir[len("DUSENLER="):].split(",") if x.strip()]
    return p.returncode, iddia, gecti, kirmizi, dusenler, ham


def mutant_kok_kur(kaynak_metin):
    kok = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-d1-mutant-"))
    tools = os.path.join(kok, "tools")
    os.makedirs(tools)
    with open(os.path.join(tools, "d1-sync.py"), "w", encoding="utf-8") as f:
        f.write(kaynak_metin)
    os.symlink(os.path.join(BURASI, KOMSU), os.path.join(tools, KOMSU))
    return kok, os.path.join(tools, "d1-sync.py")


def main():
    with open(GOVDE, encoding="utf-8") as f:
        kaynak = f.read()

    print("── TABAN (canli govde) ──")
    rc, iddia, gecti, kirmizi, dusenler, ham = bataryayi_kos(GOVDE)
    if rc != 0 or kirmizi != 0 or not iddia:
        print(ham[-3000:])
        print("!! TABAN KIRMIZI — mutasyon turu KOSMAZ (once bataryayi yesile getir).")
        return 1
    print("TABAN: IDDIA=%d GECTI=%d KIRMIZI=0" % (iddia, gecti))

    olduren = kontrol = 0
    olduren_basarili = kontrol_basarili = 0
    yama_tutmadi = []
    ulasmadi = []
    atif_tutmadi = []

    for ad, eski, yeni, beklenen in MUTANTLAR:
        sayi = kaynak.count(eski)
        if sayi < 1:
            yama_tutmadi.append(ad)
            print("!! %s — CAPA BULUNAMADI (yama TUTMADI)" % ad)
            continue
        mutant_metin = kaynak.replace(eski, yeni, 1)
        if mutant_metin == kaynak:
            yama_tutmadi.append(ad)
            print("!! %s — metin DEGISMEDI (yama TUTMADI)" % ad)
            continue
        kok, mutant_yol = mutant_kok_kur(mutant_metin)
        try:
            m_rc, m_iddia, m_gecti, m_kirmizi, m_dusenler, m_ham = bataryayi_kos(mutant_yol)
        except subprocess.TimeoutExpired:
            m_rc, m_iddia, m_gecti, m_kirmizi, m_dusenler, m_ham = (
                -1, None, None, None, ["(TUR TAVANI ASILDI)"], "")
        finally:
            shutil.rmtree(kok, ignore_errors=True)

        if beklenen:
            olduren += 1
            if m_kirmizi in (None, 0):
                ulasmadi.append(ad)
                print("!! %s — MUTANT HEDEFE ULASMADI (sonuc tabanla AYNI: KIRMIZI=%s)"
                      % (ad, m_kirmizi))
                continue
            eksik = [b for b in beklenen
                     if not any(d.startswith(b + " ") for d in m_dusenler)]
            if eksik:
                atif_tutmadi.append("%s (beklenen kol dusmedi: %s)" % (ad, ",".join(eksik)))
                print("!! %s — KIRMIZI ama HEDEF KOL DUSMEDI: %s | dusenler=%s"
                      % (ad, ",".join(eksik), m_dusenler))
                continue
            olduren_basarili += 1
            print("OLDURDU %s — KIRMIZI=%d, hedef kollar dustu: %s"
                  % (ad, m_kirmizi, ",".join(beklenen)))
        else:
            kontrol += 1
            if m_rc == 0 and m_kirmizi == 0 and m_iddia == iddia:
                kontrol_basarili += 1
                print("KONTROL YESIL %s (IDDIA=%d)" % (ad, m_iddia))
            else:
                atif_tutmadi.append("%s (KONTROL KIRMIZI YANDI)" % ad)
                print("!! %s — KONTROL MUTANTI KIRMIZI YANDI (rc=%s kirmizi=%s): %s"
                      % (ad, m_rc, m_kirmizi, m_dusenler))

    print("")
    print("MUTANT=%d/%d OLDUREN=%d/%d KONTROL=%d/%d YAMA_TUTMADI=%d ULASMADI=%d "
          "HEDEF_KOL_ATFI=%d/%d"
          % (olduren_basarili + kontrol_basarili, len(MUTANTLAR),
             olduren_basarili, olduren, kontrol_basarili, kontrol,
             len(yama_tutmadi), len(ulasmadi),
             olduren_basarili, olduren))
    if yama_tutmadi or ulasmadi or atif_tutmadi:
        for x in yama_tutmadi + ulasmadi + atif_tutmadi:
            print("  KIRMIZI: " + x)
        return 1
    print("TABAN_IDDIA=%d — mutasyon turu TEMIZ." % iddia)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
