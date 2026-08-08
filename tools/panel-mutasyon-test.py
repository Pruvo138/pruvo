#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — marka durum paneli kabul testi GERÇEKTEN ölçüyor mu?

"marka-panel-test.py yeşil" tek başına kanıt değildir: yeşil, testin neyi ölçtüğüne
bağlıdır ([[test-hatali-davranisi-kutsar]]). Bu sürücü paneli/katlama katmanını TEK TEK
bozar ve her bozmanın kabul testini KIRMIZI yaktığını ÖLÇER. Ayrıca davranışı
DEĞİŞTİRMEYEN bir KONTROL mutantı koşulur: o YEŞİL kalmalı — kalmazsa batarya
"her değişiklikte kırmızı" demektir ve hiçbir şey ölçmüyordur.

Mutasyon DAİMA geçici bir AYNA dizinine uygulanır (tools/ symlink'lenir, yalnız mutasyona
uğrayan dosya gerçek kopya olur). Canlı tools/ dizinine YAZILMAZ.

Tuzaklar kapatıldı:
  * Mutant GERÇEKTEN yüklendi mi: hedef metnin kaynakta VAR olduğu, mutasyondan sonra
    YOK olduğu ve yeni metnin VAR olduğu ölçülür ([[mutasyon-diske-yazma-tuzagi]]).
  * Bytecode önbelleği: her mutant TAZE dizinde + PYTHONDONTWRITEBYTECODE=1
    ([[mutasyon-bytecode-onbellegi]]).
  * Çökme kırmızıyla karışmasın: mutantın çıkışında kabul testinin KENDİ "SONUC:" satırı
    aranır; import çökmesi ayrı raporlanır ([[mutasyon-kaniti-yeniden-uretilebilir]]).

Çalıştır:  python3 tools/panel-mutasyon-test.py   (0 = geçti, 1 = kaldı)
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KABUL = "marka-panel-test.py"

# (ad, dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("a) önek eşleştirme kuralı ALT-DİZE'ye gevşetildi",
     "marka_katla.py",
     'if n.startswith(nm + " ") or n.startswith(nm + "-"):',
     "if nm in n:",
     True),
    ("b) marka katlama TOPLAMA yerine ÜZERİNE-YAZMA",
     "marka_katla.py",
     'cur["eklenen"] += int(k.get("eklenen", 0) or 0)',
     'cur["eklenen"] = int(k.get("eklenen", 0) or 0)',
     True),
    ("c) null -> 0 çevrimi (to-do sinyali sessizce ölür)",
     "marka_katla.py",
     '    if kayit.get("taranan", 0) > 0:\n        return 0\n    return None',
     '    if kayit.get("taranan", 0) > 0:\n        return 0\n    return 0',
     True),
    ("d) ikiz liste: KISA elle yazıldı (türetme koptu)",
     "parity-panel.py",
     "KISA = mk.PLATFORM_KISA",
     'KISA = ["Printables", "Thingiverse", "MakerWorld"]',
     True),
    ("e) eşik mantığı: AZ_ORAN sarıyı öldürüyor",
     "marka_katla.py",
     "AZ_ORAN = 0.5   #",
     "AZ_ORAN = 0.05  #",
     True),
    ("f) platform genişletmesi geri alındı (Cults3D + CGTrader düştü)",
     "marka_katla.py",
     '    ("Cults3D",     "Cults3D",     "cults3d.com"),\n'
     '    ("CGTrader",    "CGTrader",    "cgtrader.com"),\n',
     "",
     True),
    ("g) otomatik tazeleme kaldırıldı (sayfa canlı değil)",
     "parity-panel.py",
     "setInterval(tazele,TAZELEME_MS);",
     "",
     True),
    ("h) KONTROL MUTANTI (davranış DEĞİŞMEZ) — YEŞİL kalmalı",
     "marka_katla.py",
     "        return MARKA_KANONIK[n]",
     "        return MARKA_KANONIK.get(n)",
     False),
]


def ayna_kur():
    """tools/ symlink aynası + index.html symlink -> geçici kök döner."""
    kok = tempfile.mkdtemp(prefix="panel-mut-")
    os.makedirs(os.path.join(kok, "tools"))
    os.symlink(os.path.join(ROOT, "index.html"), os.path.join(kok, "index.html"))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(kok, "tools", ad))
    return kok


def kabul_kos(kok):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", KABUL)],
                       capture_output=True, text=True, env=env, timeout=300)
    return r


def mutasyon_uygula(kok, dosya, eski, yeni):
    """Symlink'i GERÇEK (mutasyonlu) kopyayla değiştir. Uygulandığını ÖLÇER."""
    hedef = os.path.join(kok, "tools", dosya)
    src = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
    if src.count(eski) != 1:
        return None, "hedef metin kaynakta %d kez geçiyor (1 olmalı)" % src.count(eski)
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return None, "mutasyon metni DEĞİŞTİRMEDİ"
    os.unlink(hedef)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(mut)
    diskte = open(hedef, encoding="utf-8").read()
    if diskte != mut:
        return None, "diske yazılan içerik beklenenden farklı"
    if eski in diskte:
        return None, "eski metin HÂLÂ diskte (mutasyon uygulanmadı)"
    if yeni and yeni not in diskte:
        return None, "yeni metin diskte YOK"
    return diskte, None


FAILS = []
print("=== KONTROL KOŞUMU (mutasyonsuz) — YEŞİL olmalı ===")
_kok = ayna_kur()
_r = kabul_kos(_kok)
_temiz = _r.returncode == 0 and "SONUC: YESIL" in _r.stdout
print("  %s  ayna üzerinde mutasyonsuz kabul testi (rc=%d)"
      % ("PASS" if _temiz else "FAIL", _r.returncode))
if not _temiz:
    FAILS.append("mutasyonsuz ayna koşumu yeşil değil")
    print(_r.stdout[-2500:])
    print(_r.stderr[-1500:])
shutil.rmtree(_kok, ignore_errors=True)

print("\n=== MUTANTLAR ===")
kirmizi_yanan = 0
beklenen_kirmizi = sum(1 for m in MUTANTLAR if m[4])
kontrol_sonuc = None
for ad, dosya, eski, yeni, kirmizi_bekle in MUTANTLAR:
    kok = ayna_kur()
    _, hata = mutasyon_uygula(kok, dosya, eski, yeni)
    if hata:
        print("  FAIL  %s -> MUTASYON UYGULANAMADI: %s" % (ad, hata))
        FAILS.append(ad + " (uygulanamadı)")
        shutil.rmtree(kok, ignore_errors=True)
        continue
    r = kabul_kos(kok)
    yesil = "SONUC: YESIL" in r.stdout
    kirmizi = "SONUC: KIRMIZI" in r.stdout
    coktu = not yesil and not kirmizi
    if kirmizi_bekle:
        ok = kirmizi and r.returncode != 0
        if ok:
            kirmizi_yanan += 1
        etiket = "KIRMIZI ✅" if ok else ("ÇÖKTÜ (kırmızıyla karışmasın)" if coktu
                                         else "YEŞİL ❌ (mutant YAKALANMADI)")
        # NOT: cokme de "yakaladi" sayilmaz — kabul testi iddiasini olcemedi demektir.
        print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, etiket))
        if not ok:
            FAILS.append(ad)
            print("        rc=%d  stderr: %s" % (r.returncode, (r.stderr or "")[-300:]))
    else:
        kontrol_sonuc = "YESIL" if (yesil and r.returncode == 0) else "KIRMIZI"
        ok = kontrol_sonuc == "YESIL"
        print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol_sonuc))
        if not ok:
            FAILS.append(ad + " (kontrol mutantı kırmızı yandı: batarya ölçmüyor)")
            print(r.stdout[-1500:])
    shutil.rmtree(kok, ignore_errors=True)

print("\nMUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
      % (kirmizi_yanan, beklenen_kirmizi, kontrol_sonuc or "KOŞULMADI"))
if FAILS:
    print("SONUC: KIRMIZI ❌  (%d)" % len(FAILS))
    sys.exit(1)
print("SONUC: YESIL ✅")
sys.exit(0)
