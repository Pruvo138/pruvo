#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sabah spec'i KIRMIZI SEVİYESİ bataryası — `kral-sabah.py::kirmizi_siniflandir`.

18 Eyl 2026 (KraL-Tamirci-18Eyl): spec `ADET=8` bastı; 3'ü o an ZATEN kapalıydı
(ardılı success), 5'i canlıydı — ikisi aynı sayıya çöküyordu ve satırda SHA yoktu.
Kırmızı artık iş akışı+dal SEVİYESİNDEN (en yeni hükümlü ardıl) okunur.

Her vaka SAF fonksiyonu sahte koşum listesiyle çağırır: gh YOK, ağ YOK, disk
yazımı yalnız tempfile (fake gh + mutant kopyası; TemporaryDirectory temizler).

  V1 ardılı success                     -> KAPANDI, canli=0 kapanan=1
  V2 ardıl yok                          -> CANLI: ardıl hüküm YOK
  V3 ardıl yalnız cancelled             -> CANLI (cancelled hüküm DEĞİL)
  V4 ardıllar failure sonra success     -> KAPANDI (EN YENİ hüküm; liste sırası karışık)
  V5 ardıllar success sonra failure     -> CANLI: ardılı failure
  V6 başka iş akışının success'i        -> kapatmaz (ad ekseni)
  V7 başka dalın success'i              -> kapatmaz (dal ekseni)
  V8 ardıl sürüyor                      -> CANLI ∧ hükümsüz kovasında görünür
  V9 18 Eyl 03:20Z anlık görüntüsü      -> ADET=8 · CANLI=5 · ARDILI_YESIL=3
  V10 bugunun_kirmizilari (fake gh)     -> blok `CANLI=` taşır ∧ ADET TÜM kırmızılar (anlam değişmedi)
  M1 MUTANT ardil_hukum hep None        -> V1 KIRMIZI
  M2 MUTANT ad ekseni düşer             -> V6 KIRMIZI
  M3 MUTANT en-yeni seçimi ilk-bulunan  -> V4 KIRMIZI
  (her mutantta kontrol V2 YEŞİL kalır — hedef-kol atfı)

K435 (8 Eki 2026, KraL-Tamirci-8Eki) — DAL kırmızısı main'e MERGE edilip dal silinince
ardıl aynı dalda hiç doğmaz; spec onu gün sonuna dek CANLI sayıyordu. Ardıl artık
ana daldaki aynı iş akışının koşumundan da okunur, YALNIZ kırmızının commit'i o
koşumun commit'inin ATASIYSA (`ata_mi`, gerçekte `git merge-base --is-ancestor`):
  V16 dal kırmızısı + main ardılı success + ata      -> KAPANDI "dal main'e katıldı"
  V17 aynı ama ata DEĞİL                              -> CANLI
  V18 main ardılı failure (ata)                       -> CANLI: ardılı failure
  V19 ata ölçülemedi (None) / ata_mi verilmedi        -> CANLI (görünür yön)
  V20 main ardılı BAŞKA iş akışının success'i         -> CANLI
  V21 main koşumu kırmızıdan ÖNCE açılmış             -> CANLI (ardıl olamaz)
  V22 başka DAL'ın success'i (ata olsa bile)          -> CANLI
  V23 gerçek git (geçici depo): ata True/False/None   -> ata_mi_git sözleşmesi
  V24 ANA dal kırmızısı + yan dal success (ata)       -> CANLI (main kırmızısı yalnız main ardılıyla kapanır)
  V25 bugunun_kirmizilari uçtan uca (fake gh+ata)     -> blok CANLI=0 · ARDILI_YESIL=1 · "main'e katıldı"
  M7 MUTANT ata testi kalkar                     -> V17 KIRMIZI
  M8 MUTANT ata bilinmiyor=ata sayılır           -> V19 KIRMIZI
  M9 MUTANT ana-dal şartı düşer (her dal ardıl)  -> V22 KIRMIZI
  M10 MUTANT git hata=ata (None yerine True)     -> V23 KIRMIZI
  M11 MUTANT bugunun_kirmizilari ata_mi'yi geçirmez -> V25 KIRMIZI

K435 (11 Eki 2026, KraL-Tamirci-11Eki) — spec üretildiği anda main'in ardıl SERIT B koşumları
KOŞUYORDU; `cancelled` kırmızı "CANLI: ardıl hüküm YOK" bastı ve Tamirci sahte iş aradı
(9/10/11 Eki: 3 gün, 3/3). Sayı DEĞİŞMEZ (V8 sözleşmesi: görünür yön); satır "ARDIL SÜRÜYOR:
run <id> <durum> @<sha> — hükmü bekle" der, başlık `ARDIL_SURUYOR=N` taşır:
  V26 hükümlü ardıl yok + aynı iş akışı/dal'da in_progress|pending ardıl -> etiket, CANLI AYNI
  V27 başka iş akışı · başka dal · kırmızıdan ÖNCE · tamamlanmış cancelled -> etiket YOK
  V28 hükümlü failure ardıl VARKEN etiket YOK; o failure'ın koşan ardılı varsa onda VAR
  V29 bugunun_kirmizilari uçtan uca (fake gh) -> `ARDIL_SURUYOR=1` / kontrol `=0`
  M12 MUTANT koşan/tamam ayrımı düşer           -> V27 KIRMIZI
  M13 MUTANT etiket kapsamı `ardil is None`ten genişler -> V28 KIRMIZI
  M14 MUTANT başlık sayacı 0'a sabitlenir       -> V29 KIRMIZI

K435 (12 Eki 2026, KraL-Tamirci-12Eki) — "commit-tree merge boşluğu": dal main'e SQUASH /
PARÇA PARÇA / cherry-pick ile girince kırmızının SHA'sı main atası DEĞİL (`ata_mi` False) →
kırmızı gün sonuna dek CANLI. ÖLÇÜLDÜ: 12 Eki spec'i `CANLI=1` = SERIT B `38188955858`
@`f67920c6` (`kral/k80-zaman-12eki`, cancelled); içeriği main'e "foto 6 model parça 1/4..4/4"
olarak girdi (`git merge-base --is-ancestor` rc 1) ama dalın KENDİ 26 dosyası `8834edb0`'da
BİREBİR aynı. Ardıl artık İÇERİKTEN de okunur (`icerik_mi`, gerçekte `icerik_main_de_mi_git`):
  V30 ata DEĞİL ∧ içerik VAR ∧ main ardılı success   -> KAPANDI "dal İÇERİĞİ main'e girdi"
  V31 ata VAR (içerik de VAR/yok)                    -> etiket "dal main'e katıldı" (ata önce)
  V32 içerik YOK / ölçülemedi / verilmedi            -> CANLI (görünür yön)
  V33 içerik VAR ama ardıl failure · başka iş akışı · başka dal · kırmızıdan ÖNCE -> CANLI
  V34 gerçek git: kısmi iniş False · tam iniş True (ata False) · sonradan değişmiş False ·
      merge-base'in kendisi False · bilinmeyen sha None
  V35 bugunun_kirmizilari uçtan uca (fake gh+ata False+içerik True) -> CANLI=0 · "İÇERİĞİ"
  M15 MUTANT içerik sonucu bakılmaz (callable=var)    -> V32 KIRMIZI
  M16 MUTANT içerik bilinmiyor=var sayılır            -> V32 KIRMIZI
  M17 MUTANT etiket hep "dal main'e katıldı"          -> V30 KIRMIZI
  M18 MUTANT git: dosya kesişimi bakılmaz (hep True)  -> V34 KIRMIZI
  M19 MUTANT git: merge-base hatası=True (None değil) -> V34 KIRMIZI
  M20 MUTANT bugunun_kirmizilari icerik_mi'yi geçirmez -> V35 KIRMIZI

Koşum: python3 tools/sabah-ardil-kova-test.py   (rc=0 = hepsi beklenen)
"""

import datetime as dt
import importlib.util
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "tools", "sabah-teslim", "kral-sabah.py")

GUN = dt.date(2026, 9, 18)
SB = "Nöbet şeridi (SERIT B — yayını BLOKLAMAZ)"
BD = "Build & deploy to GitHub Pages"

MUTANTLAR = {
    "M1": ("    return en_yeni\n", "    return None  # MUTANT\n", "V1"),
    "M2": ('        if d.get("name") != run.get("name"):\n',
           '        if False:  # MUTANT\n', "V6"),
    "M3": ("        if en_yeni_t is None or t > en_yeni_t:\n",
           "        if en_yeni_t is None:  # MUTANT\n", "V4"),
    # 19 Eyl — DEVREDEN CANLI ekseni
    "M4": ("        if conc not in KIRMIZI_KUME or t.date() >= bugun:\n",
           "        if conc not in KIRMIZI_KUME:  # MUTANT\n", "V14"),
    "M5": ("        if ad not in son or t > son[ad][0]:\n",
           "        if ad not in son:  # MUTANT\n", "V12"),
    "M6": ("                + devreden, 0, kaynak)\n",
           "                , 0, kaynak)  # MUTANT\n", "V15"),
    # 8 Eki — K435: dal kırmızısının ardılı main'de
    "M7": ("    if ata_mi is not None and ata_mi(a, b) is True:\n        return True\n",
           "    if ata_mi is not None:  # MUTANT\n        return True\n", "V17"),
    "M8": ("    if ata_mi is not None and ata_mi(a, b) is True:\n        return True\n",
           "    if ata_mi is not None and ata_mi(a, b) is not False:  # MUTANT\n        return True\n",
           "V19"),
    "M9": ('    if (ata_mi is None and icerik_mi is None) or d.get("headBranch") != ANA_DAL:\n',
           "    if ata_mi is None and icerik_mi is None:  # MUTANT\n", "V22"),
    "M10": ("    if r.returncode == 1:\n        return False\n    return None\n",
            "    if r.returncode == 1:\n        return False\n    return True  # MUTANT\n", "V23"),
    "M11": ("kirmizi_siniflandir(\n            data, bugun, ata_mi_git, icerik_main_de_mi_git)\n",
            "kirmizi_siniflandir(data, bugun)  # MUTANT\n", "V25"),
    # 11 Eki — K435: ardıl SÜRÜYOR etiketi
    "M12": ("        if tamam == suruyor:\n",
            "        if False:  # MUTANT\n", "V27"),
    "M13": ("                bekleyen = (ardil_hukum(data, run, ata_mi, suruyor=True, icerik_mi=icerik_mi)\n"
            "                            if ardil is None else None)\n",
            "                bekleyen = ardil_hukum(data, run, ata_mi, suruyor=True, icerik_mi=icerik_mi)  # MUTANT\n",
            "V28"),
    "M14": ('            suruyor_n = len([x for x in kirmizi if "ARDIL SÜRÜYOR" in x])\n',
            "            suruyor_n = 0  # MUTANT\n", "V29"),
    # 12 Eki — K435: SHA ata değil ama İÇERİK main'de (squash / parça / cherry-pick)
    "M15": ("    return icerik_mi is not None and icerik_mi(a, b) is True\n",
            "    return icerik_mi is not None  # MUTANT\n", "V32"),
    "M16": ("    return icerik_mi is not None and icerik_mi(a, b) is True\n",
            "    return icerik_mi is not None and icerik_mi(a, b) is not False  # MUTANT\n", "V32"),
    "M17": ('                        "dal main\'e katıldı" if ata else\n',
            '                        "dal main\'e katıldı" if True else\n', "V30"),
    "M18": ("                sonuc = not (kendi_k & fark_k)\n",
            "                sonuc = True  # MUTANT\n", "V34"),
    "M19": ("        if mb.returncode != 0 or not mb.stdout.strip():\n            sonuc = None\n",
            "        if mb.returncode != 0 or not mb.stdout.strip():\n            sonuc = True  # MUTANT\n",
            "V34"),
    "M20": ("kirmizi_siniflandir(\n            data, bugun, ata_mi_git, icerik_main_de_mi_git)\n",
            "kirmizi_siniflandir(\n            data, bugun, ata_mi_git)  # MUTANT\n", "V35"),
}


def modul_yukle(yol, ad):
    s = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def k(ad, saat, conc, sha, rid, dal="main", durum="completed", gun=GUN):
    return {"name": ad, "headBranch": dal, "status": durum, "conclusion": conc,
            "createdAt": "%sT%sZ" % (gun.isoformat(), saat), "headSha": sha + "0" * 32,
            "databaseId": rid}


def vakalar(mod, gun=GUN):
    s = lambda data: mod.kirmizi_siniflandir(data, gun)
    kk = lambda *a, **kw: k(*a, gun=gun, **kw)
    sonuc = {}

    r, _, c, kp = s([kk(BD, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V1"] = (c == 0 and kp == 1 and "KAPANDI" in r[0] and "`bbbbbbbb`" in r[0], r)

    r, _, c, kp = s([kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V2"] = (c == 1 and kp == 0 and "CANLI: ardıl hüküm YOK" in r[0], r)

    r, _, c, kp = s([kk(BD, "02:00:00", "cancelled", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V3"] = (c == 2 and kp == 0 and satir and "CANLI: ardıl hüküm YOK" in satir[0], r)

    r, _, c, kp = s([kk(BD, "01:00:00", "failure", "aaaaaaaa", 1),
                     kk(BD, "02:00:00", "failure", "bbbbbbbb", 2),
                     kk(BD, "03:00:00", "success", "cccccccc", 3)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V4"] = (kp == 2 and c == 0 and satir and "`cccccccc` success" in satir[0], r)

    r, _, c, kp = s([kk(BD, "03:00:00", "failure", "cccccccc", 3),
                     kk(BD, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V5"] = (satir and "CANLI: ardılı `cccccccc` failure" in satir[0] and c == 2, r)

    r, _, c, kp = s([kk(SB, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V6"] = (c == 1 and kp == 0, r)

    r, _, c, kp = s([kk(BD, "02:00:00", "success", "bbbbbbbb", 2, dal="yan-dal"),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V7"] = (c == 1 and kp == 0, r)

    r, h, c, kp = s([kk(BD, "02:00:00", None, "bbbbbbbb", 2, durum="in_progress"),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V8"] = (c == 1 and len(h) == 1 and "sürüyor" in h[0], (r, h))

    # 18 Eyl 03:20Z anlık görüntüsü (gh run list, main, yeni→eski) — ölçülmüş koşumlar
    gercek = [
        kk(SB, "03:10:24", None, "84a60965", 35302195200, durum="in_progress"),
        kk(BD, "03:10:24", None, "84a60965", 35302195010, durum="in_progress"),
        kk(BD, "01:56:47", "success", "45616be8", 35297362223),
        kk(SB, "01:56:47", "failure", "45616be8", 35297362459),
        kk(SB, "01:35:35", "cancelled", "3e080a2c", 35295949469),
        kk(BD, "01:08:20", "failure", "6f01d13b", 35294096925),
        kk(SB, "01:08:20", "cancelled", "6f01d13b", 35294097073),
        kk(BD, "01:00:26", "cancelled", "fe082f84", 35293542967),
        kk(SB, "01:00:26", "cancelled", "fe082f84", 35293543235),
        kk(SB, "00:58:23", "cancelled", "6a3a6bfb", 35293398171),
        kk(BD, "00:58:22", "cancelled", "6a3a6bfb", 35293397856),
    ]
    r, h, c, kp = s(gercek)
    sonuc["V9"] = (len(r) == 8 and c == 5 and kp == 3 and len(h) == 2, (len(r), c, kp, len(h)))

    # --- DEVREDEN CANLI ekseni (19 Eyl 2026, KraL-Tamirci-19Eyl) ------------------
    dv = lambda data, b=gun: mod.devreden_canlilar(data, b)
    dun = gun - dt.timedelta(days=1)
    kd = lambda *a, **kw: k(*a, gun=dun, **kw)
    # V11: 19 Eyl 03:20Z ölçülmüş anlık görüntü (bugün=gun) — SERIT B dün 3 kez failure,
    # o an bugün açılmış koşum YOK (05:08Z schedule spec'ten SONRA açıldı, cancelled);
    # Build&deploy dün success. Eski kod bunu "ADET=0 · kırmızı yok" diye bastı.
    anlik = [kd(SB, "22:50:08", "failure", "3d73bc45", 35403252251),
             kd(SB, "19:13:05", "failure", "3d73bc45", 35384686461),
             kd(BD, "15:17:23", "success", "3d73bc45", 35361503500),
             kd(SB, "15:17:23", "failure", "3d73bc45", 35361503557)]
    r = dv(anlik)
    r0, _, c0, _ = s(anlik)
    sonuc["V11"] = (len(r) == 1 and "35403252251" in r[0] and "DEVREDEN CANLI" in r[0]
                    and c0 == 0, (r, c0))
    # V12: dünkü failure'ın ardılı (dün, daha geç) success -> devreden YOK.
    r = dv([kd(SB, "10:00:00", "failure", "aaaaaaaa", 1),
            kd(SB, "20:00:00", "success", "bbbbbbbb", 2)])
    sonuc["V12"] = (r == [], r)
    # V13: main dışı dalın dünkü failure'ı -> devreden YOK (dal ekseni).
    r = dv([kd(SB, "10:00:00", "failure", "aaaaaaaa", 1, dal="claude/x")])
    sonuc["V13"] = (r == [], r)
    # V14: en-yeni kırmızı BUGÜN açıldı -> ana eksende CANLI, devreden'de ÇİFT SAYILMAZ.
    r = dv([kd(SB, "10:00:00", "failure", "aaaaaaaa", 1),
            kk(SB, "01:00:00", "failure", "bbbbbbbb", 2)])
    sonuc["V14"] = (r == [], r)

    # --- K435: DAL kırmızısının ardılı main'de (8 Eki 2026) -----------------------
    sa = lambda data, ata=None: mod.kirmizi_siniflandir(data, gun, ata)
    EVET, HAYIR, BILINMEZ = (lambda a, b: True), (lambda a, b: False), (lambda a, b: None)
    DAL = "kral/x"
    kirmizi_dal = kk(SB, "01:00:00", "failure", "aaaaaaaa", 1, dal=DAL)

    r, _, c, kp = sa([kk(SB, "02:00:00", "success", "bbbbbbbb", 2), kirmizi_dal], EVET)
    sonuc["V16"] = (c == 0 and kp == 1 and "KAPANDI: dal main'e katıldı" in r[0]
                    and "`bbbbbbbb`" in r[0], r)

    r, _, c, kp = sa([kk(SB, "02:00:00", "success", "bbbbbbbb", 2), kirmizi_dal], HAYIR)
    sonuc["V17"] = (c == 1 and kp == 0 and "CANLI: ardıl hüküm YOK" in r[0], r)

    r, _, c, kp = sa([kk(SB, "02:00:00", "failure", "bbbbbbbb", 2), kirmizi_dal], EVET)
    satir = [x for x in r if "run 1 " in x]
    sonuc["V18"] = (c == 2 and kp == 0 and satir and "CANLI: ardılı `bbbbbbbb` failure" in satir[0], r)

    veri = [kk(SB, "02:00:00", "success", "bbbbbbbb", 2), kirmizi_dal]
    r1, _, c1, kp1 = sa(veri, BILINMEZ)
    r2, _, c2, kp2 = sa(veri)  # ata_mi hiç verilmedi: eski sözleşme
    sonuc["V19"] = (c1 == 1 and kp1 == 0 and c2 == 1 and kp2 == 0, (r1, r2))

    r, _, c, kp = sa([kk(BD, "02:00:00", "success", "bbbbbbbb", 2), kirmizi_dal], EVET)
    sonuc["V20"] = (c == 1 and kp == 0, r)

    r, _, c, kp = sa([kk(SB, "00:30:00", "success", "bbbbbbbb", 2), kirmizi_dal], EVET)
    sonuc["V21"] = (c == 1 and kp == 0, r)

    r, _, c, kp = sa([kk(SB, "02:00:00", "success", "bbbbbbbb", 2, dal="kral/y"), kirmizi_dal], EVET)
    sonuc["V22"] = (c == 1 and kp == 0, r)

    sonuc["V23"] = v23_git_ata(mod)

    r, _, c, kp = sa([kk(SB, "02:00:00", "success", "bbbbbbbb", 2, dal="kral/y"),
                      kk(SB, "01:00:00", "failure", "aaaaaaaa", 1, dal="main")], EVET)
    sonuc["V24"] = (c == 1 and kp == 0, r)

    # --- K435 (11 Eki): ardıl SÜRÜYOR etiketi — SAYI değişmez, satır "hükmü bekle" der ----
    ETIKET = "ARDIL SÜRÜYOR"
    # V26: hükümlü ardıl YOK + aynı iş akışı/dal'da KOŞAN (in_progress | pending) ardıl VAR
    # -> CANLI sayısı AYNI (görünür yön), satır koşan ardılın run/durum/sha'sını taşır.
    r, _, c, kp = s([kk(SB, "02:00:00", None, "bbbbbbbb", 2, durum="in_progress"),
                     kk(SB, "01:00:00", "cancelled", "aaaaaaaa", 1)])
    r2, _, c2, kp2 = s([kk(SB, "02:00:00", None, "bbbbbbbb", 2, durum="pending"),
                        kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V26"] = (c == 1 and kp == 0 and "CANLI: ardıl hüküm YOK" in r[0]
                    and "ARDIL SÜRÜYOR: run 2 in_progress @`bbbbbbbb`" in r[0]
                    and "ŞİMDİ TAMİR ETME" in r[0]
                    and c2 == 1 and kp2 == 0
                    and "ARDIL SÜRÜYOR: run 2 pending @`bbbbbbbb`" in r2[0], (r, r2))
    # V27: koşan ardıl SAYILMAZ — başka iş akışı · başka dal · kırmızıdan ÖNCE açılmış ·
    # koşan DEĞİL tamamlanmış `cancelled` (hüküm değil ama sürmüyor da) -> etiket YOK.
    olumsuz = {
        "ad": [kk(BD, "02:00:00", None, "bbbbbbbb", 2, durum="in_progress"),
               kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)],
        "dal": [kk(SB, "02:00:00", None, "bbbbbbbb", 2, dal="yan-dal", durum="in_progress"),
                kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)],
        "zaman": [kk(SB, "00:30:00", None, "bbbbbbbb", 2, durum="in_progress"),
                  kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)],
        "iptal": [kk(SB, "02:00:00", "cancelled", "bbbbbbbb", 2),
                  kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)],
    }
    v27 = {}
    for ad_, veri_ in olumsuz.items():
        rr, _, cc, _kp = s(veri_)
        satir_ = [x for x in rr if "run 1 " in x]
        v27[ad_] = bool(satir_) and ETIKET not in satir_[0] and cc >= 1
    sonuc["V27"] = (all(v27.values()), v27)
    # V28: hükümlü (failure) ardıl VARKEN etiket YOK (kapsam daraltması: görünür yön) —
    # ama o failure'ın KENDİSİ için koşan ardıl varsa onun satırında etiket VAR.
    r, _, c, kp = s([kk(SB, "03:00:00", None, "cccccccc", 3, durum="in_progress"),
                     kk(SB, "02:00:00", "failure", "bbbbbbbb", 2),
                     kk(SB, "01:00:00", "failure", "aaaaaaaa", 1)])
    s1 = [x for x in r if "run 1 " in x]
    s2 = [x for x in r if "run 2 " in x]
    sonuc["V28"] = (c == 2 and bool(s1) and ETIKET not in s1[0]
                    and "CANLI: ardılı `bbbbbbbb` failure" in s1[0]
                    and bool(s2) and "ARDIL SÜRÜYOR: run 3 in_progress" in s2[0], r)

    # --- K435 (12 Eki): SHA ata DEĞİL ama İÇERİK main'de (squash / parça / cherry-pick) -------
    si = lambda data, ata=None, ic=None: mod.kirmizi_siniflandir(data, gun, ata, ic)
    ok_main = kk(SB, "02:00:00", "success", "bbbbbbbb", 2)
    r, _, c, kp = si([ok_main, kirmizi_dal], HAYIR, EVET)
    sonuc["V30"] = (c == 0 and kp == 1 and "KAPANDI: dal İÇERİĞİ main'e girdi" in r[0]
                    and "SHA ata değil" in r[0] and "`bbbbbbbb`" in r[0]
                    and "dal main'e katıldı" not in r[0], r)
    r1, _, c1, kp1 = si([ok_main, kirmizi_dal], EVET, EVET)
    r2, _, c2, kp2 = si([ok_main, kirmizi_dal], EVET, HAYIR)
    r3, _, c3, kp3 = si([ok_main, kirmizi_dal], EVET)
    sonuc["V31"] = (c1 == c2 == c3 == 0 and kp1 == kp2 == kp3 == 1
                    and all("KAPANDI: dal main'e katıldı" in x[0] and "İÇERİĞİ" not in x[0]
                            for x in (r1, r2, r3)), (r1, r2, r3))
    v32 = {}
    for ad_, (ata_, ic_) in {"icerik-yok": (HAYIR, HAYIR), "icerik-bilinmez": (HAYIR, BILINMEZ),
                             "icerik-verilmedi": (HAYIR, None),
                             "ata-bilinmez-icerik-yok": (BILINMEZ, HAYIR)}.items():
        rr, _, cc, kpp = si([ok_main, kirmizi_dal], ata_, ic_)
        v32[ad_] = (cc == 1 and kpp == 0 and "CANLI: ardıl hüküm YOK" in rr[0])
    sonuc["V32"] = (all(v32.values()), v32)
    v33 = {}
    olumsuz33 = {
        "failure": [kk(SB, "02:00:00", "failure", "bbbbbbbb", 2), kirmizi_dal],
        "ad": [kk(BD, "02:00:00", "success", "bbbbbbbb", 2), kirmizi_dal],
        "dal": [kk(SB, "02:00:00", "success", "bbbbbbbb", 2, dal="kral/y"), kirmizi_dal],
        "zaman": [kk(SB, "00:30:00", "success", "bbbbbbbb", 2), kirmizi_dal],
    }
    for ad_, veri_ in olumsuz33.items():
        rr, _, cc, kpp = si(veri_, HAYIR, EVET)
        satir_ = [x for x in rr if "run 1 " in x]
        v33[ad_] = bool(satir_) and "CANLI" in satir_[0] and "KAPANDI" not in satir_[0] and kpp == 0
    sonuc["V33"] = (all(v33.values()), v33)
    sonuc["V34"] = v34_git_icerik(mod)
    return sonuc


def v34_git_icerik(mod):
    """Gerçek git, geçici depo: ata DEĞİL ama içerik main'de. base(a,b) -> dal(a,b değişir) ;
    main: base -> kısmi(yalnız a) -> tam(a+b: dalın 2 dosyası da) -> sonra(a yine değişir).
    icerik(dal,kısmi)=False · (dal,tam)=True ∧ ata(dal,tam)=False · (dal,sonra)=False ·
    (dal,base)=False · bilinmeyen sha=None. GIT_* ortamı TEMİZLENİR (V23 ile aynı gerekçe)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from git_ortami import sentetik_git
    temiz = {a: v for a, v in os.environ.items() if a.startswith("GIT_")}
    for a in temiz:
        del os.environ[a]
    try:
        with tempfile.TemporaryDirectory() as td:
            kw = dict(ayarlar=("-c", "commit.gpgsign=false"), capture_output=True, text=True)
            g = lambda *a: sentetik_git(td, *a, **kw)

            def yaz(ad, metin):
                with open(os.path.join(td, ad), "w", encoding="utf-8") as f:
                    f.write(metin)

            def sha():
                return g("rev-parse", "HEAD").stdout.strip()

            g("init", "-q", "-b", "main")
            yaz("a.txt", "a0\n")
            yaz("b.txt", "b0\n")
            g("add", "-A")
            g("commit", "-q", "-m", "base")
            base = sha()
            g("checkout", "-q", "-b", "dal")
            yaz("a.txt", "a1\n")
            yaz("b.txt", "b1\n")
            g("commit", "-q", "-am", "dal")
            dal = sha()
            g("checkout", "-q", "main")
            yaz("a.txt", "a1\n")
            g("commit", "-q", "-am", "kismi")
            kismi = sha()
            yaz("b.txt", "b1\n")
            g("commit", "-q", "-am", "tam")
            tam = sha()
            yaz("a.txt", "a2\n")
            g("commit", "-q", "-am", "sonra")
            sonra = sha()
            eski = mod.REPO
            mod.REPO = type(mod.REPO)(td)
            mod._ICERIK_ONBELLEK.clear()
            try:
                r = (mod.icerik_main_de_mi_git(dal, kismi), mod.icerik_main_de_mi_git(dal, tam),
                     mod.ata_mi_git(dal, tam), mod.icerik_main_de_mi_git(dal, sonra),
                     mod.icerik_main_de_mi_git(dal, base),
                     mod.icerik_main_de_mi_git("0" * 40, tam))
            finally:
                mod.REPO = eski
                mod._ICERIK_ONBELLEK.clear()
    finally:
        os.environ.update(temiz)
    return r == (False, True, False, False, False, None) and len(dal) == 40, r


def v23_git_ata(mod):
    """Gerçek git, geçici depo: A -> B zinciri. ata(A,B)=True · ata(B,A)=False ·
    bilinmeyen sha=None. GIT_* ortamı TEMİZLENİR (hook/ayna koşumundan miras kalan
    GIT_DIR geçici depo yerine gerçek depoya yazdırırdı)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from git_ortami import sentetik_git  # kanonik GIT_* scrub (fikstur-git-sizinti-kapisi)
    temiz = {a: v for a, v in os.environ.items() if a.startswith("GIT_")}
    for a in temiz:
        del os.environ[a]
    try:
        with tempfile.TemporaryDirectory() as td:
            kw = dict(ayarlar=("-c", "commit.gpgsign=false"), capture_output=True, text=True)
            sentetik_git(td, "init", "-q", **kw)
            sentetik_git(td, "commit", "-q", "--allow-empty", "-m", "a", **kw)
            a_sha = sentetik_git(td, "rev-parse", "HEAD", **kw).stdout.strip()
            sentetik_git(td, "commit", "-q", "--allow-empty", "-m", "b", **kw)
            b_sha = sentetik_git(td, "rev-parse", "HEAD", **kw).stdout.strip()
            eski = mod.REPO
            mod.REPO = type(mod.REPO)(td)
            try:
                r = (mod.ata_mi_git(a_sha, b_sha), mod.ata_mi_git(b_sha, a_sha),
                     mod.ata_mi_git("0" * 40, b_sha))
            finally:
                mod.REPO = eski
    finally:
        os.environ.update(temiz)
    return r == (True, False, None) and len(a_sha) == 40, r


def v25_ata_uctan_uca(mod):
    """bugunun_kirmizilari (fake gh + sahte ata) -> dal kırmızısı main ardılıyla KAPANIR;
    classifier'a `ata_mi_git` GEÇİRİLDİĞİNİN (kablo) ölçüsü: sahte ata her zaman True."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    import json
    data = [k(SB, "00:00:02", "success", "bbbbbbbb", 2, gun=bugun),
            k(SB, "00:00:01", "failure", "aaaaaaaa", 1, gun=bugun, dal="kral/x")]
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        eski = (mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        mod.REPO = type(mod.REPO)(td)
        mod.ata_mi_git = lambda a, b: True
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git = eski
    ok = (hukum == "OK" and adet == 1 and "**CANLI=0**" in blok and "ARDILI_YESIL=1" in blok
          and "dal main'e katıldı" in blok)
    return ok, (hukum, adet, blok[:200])


def v35_icerik_uctan_uca(mod):
    """bugunun_kirmizilari (fake gh + ata False + içerik True) -> dal kırmızısı main ardılıyla
    İÇERİKTEN KAPANIR; classifier'a `icerik_main_de_mi_git` GEÇİRİLDİĞİNİN (kablo) ölçüsü."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    import json
    data = [k(SB, "00:00:02", "success", "bbbbbbbb", 2, gun=bugun),
            k(SB, "00:00:01", "cancelled", "aaaaaaaa", 1, gun=bugun, dal="kral/x")]
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        eski = (mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git, mod.icerik_main_de_mi_git)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        mod.REPO = type(mod.REPO)(td)
        mod.ata_mi_git = lambda a, b: False
        mod.icerik_main_de_mi_git = lambda a, b: True
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            (mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git,
             mod.icerik_main_de_mi_git) = eski
    ok = (hukum == "OK" and adet == 1 and "**CANLI=0**" in blok and "ARDILI_YESIL=1" in blok
          and "dal İÇERİĞİ main'e girdi" in blok)
    return ok, (hukum, adet, blok[:260])


def _fake_gh_blok(mod, data):
    """bugunun_kirmizilari'yi fake gh + sahte ata ile koşar (ağ YOK) -> (hukum, blok, adet)."""
    import json
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        eski = (mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        mod.REPO = type(mod.REPO)(td)
        mod.ata_mi_git = lambda a, b: False
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            mod.gh_yolu, mod._repo_slug, mod.REPO, mod.ata_mi_git = eski
    return hukum, blok, adet


def v29_ardil_suruyor_uctan_uca(mod):
    """K435 (11 Eki): başlık `ARDIL_SURUYOR=N` taşır; CANLI ve ADET anlamı DEĞİŞMEZ.
    Koşan ardıllı kırmızı -> CANLI=1 ∧ ARDIL_SURUYOR=1; ardılsız kırmızı -> ARDIL_SURUYOR=0."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    bekleyen = [k(SB, "00:00:02", None, "bbbbbbbb", 2, gun=bugun, durum="in_progress"),
                k(SB, "00:00:01", "cancelled", "aaaaaaaa", 1, gun=bugun)]
    kontrol = [k(SB, "00:00:01", "failure", "aaaaaaaa", 1, gun=bugun)]
    hk1, blok1, adet1 = _fake_gh_blok(mod, bekleyen)
    hk0, blok0, adet0 = _fake_gh_blok(mod, kontrol)
    ok = (hk1 == "OK" and adet1 == 1 and "**CANLI=1**" in blok1
          and "ARDIL_SURUYOR=1" in blok1 and "ARDIL SÜRÜYOR: run 2 in_progress" in blok1
          and hk0 == "OK" and adet0 == 1 and "**CANLI=1**" in blok0
          and "ARDIL_SURUYOR=0" in blok0 and "ARDIL SÜRÜYOR:" not in blok0)
    return ok, (hk1, adet1, blok1[:260], hk0, adet0, blok0[:200])


def v10_uctan_uca(mod):
    """bugunun_kirmizilari'yi fake gh ile koşar (ağ YOK)."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    import json
    data = [k(BD, "00:00:02", "success", "bbbbbbbb", 2, gun=bugun),
            k(BD, "00:00:01", "failure", "aaaaaaaa", 1, gun=bugun),
            k(SB, "00:00:01", "failure", "cccccccc", 3, gun=bugun)]
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        # REPO da kuma çevrilir: araç `cwd=REPO` (sabit Mac yolu) ile koşar; CI koşucusunda
        # o dizin YOK -> subprocess FileNotFoundError -> OLCULEMEDI (18 Eyl run 35346692885).
        eski = (mod.gh_yolu, mod._repo_slug, mod.REPO)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        mod.REPO = type(mod.REPO)(td)
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            mod.gh_yolu, mod._repo_slug, mod.REPO = eski
    ok = (hukum == "OK" and adet == 2 and "**CANLI=1**" in blok and "ARDILI_YESIL=1" in blok)
    return ok, (hukum, adet, blok[:160])


def v15_devreden_uctan_uca(mod):
    """Bugün kırmızı YOK ama dünden devreden main kırmızısı var -> ADET=0 (k333 anlamı
    korunur) ∧ blok `DEVREDEN_CANLI=1` taşır (19 Eyl'in birebir sahte-yeşil hâli)."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    dun = bugun - dt.timedelta(days=1)
    import json
    data = [k(SB, "22:50:08", "failure", "3d73bc45", 8, gun=dun),
            k(BD, "15:17:23", "success", "3d73bc45", 7, gun=dun)]
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        eski = (mod.gh_yolu, mod._repo_slug, mod.REPO)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        mod.REPO = type(mod.REPO)(td)
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            mod.gh_yolu, mod._repo_slug, mod.REPO = eski
    ok = (adet == 0 and "**DEVREDEN_CANLI=1**" in blok and "run 8" in blok)
    return ok, (hukum, adet, blok[-240:])


def main():
    mod = modul_yukle(KAYNAK, "kral_sabah_test")
    kirmizi = 0

    for ad, (ok, kanit) in sorted(vakalar(mod).items(), key=lambda x: int(x[0][1:])):
        print("%s %s %s" % ("YESIL " if ok else "KIRMIZI", ad, "" if ok else kanit))
        kirmizi += 0 if ok else 1
    ok, kanit = v10_uctan_uca(mod)
    print("%s V10 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1
    ok, kanit = v15_devreden_uctan_uca(mod)
    print("%s V15 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1
    ok, kanit = v25_ata_uctan_uca(mod)
    print("%s V25 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1
    ok, kanit = v29_ardil_suruyor_uctan_uca(mod)
    print("%s V29 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1
    ok, kanit = v35_icerik_uctan_uca(mod)
    print("%s V35 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1

    with open(KAYNAK, encoding="utf-8") as f:
        govde = f.read()
    oldu = 0
    for mad, (capa, yama, hedef) in sorted(MUTANTLAR.items()):
        if govde.count(capa) != 1:
            print("KIRMIZI %s capa adedi=%d (beklenen 1)" % (mad, govde.count(capa)))
            kirmizi += 1
            continue
        with tempfile.TemporaryDirectory() as td:
            yol = os.path.join(td, "kral_sabah_mutant.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde.replace(capa, yama))
            mm = modul_yukle(yol, "kral_sabah_" + mad)
            sonuc = vakalar(mm)
            sonuc["V15"] = v15_devreden_uctan_uca(mm)
            sonuc["V25"] = v25_ata_uctan_uca(mm)
            sonuc["V29"] = v29_ardil_suruyor_uctan_uca(mm)
            sonuc["V35"] = v35_icerik_uctan_uca(mm)
        hedef_dustu = not sonuc[hedef][0]
        kontrol = sonuc["V2"][0]
        ok = hedef_dustu and kontrol
        oldu += 1 if ok else 0
        print("%s %s hedef=%s dustu=%d kontrol_V2=%d" % (
            "YESIL " if ok else "KIRMIZI", mad, hedef, int(hedef_dustu), int(kontrol)))
        kirmizi += 0 if ok else 1

    print("SABAH_ARDIL_KOVA VAKA=35 MUTANT_OLDU=%d/%d KIRMIZI=%d rc=%d" % (
        oldu, len(MUTANTLAR), kirmizi, 1 if kirmizi else 0))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
