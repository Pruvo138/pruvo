#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA MODEL ÇİPİ KAPISI — MUTASYON SÜRÜCÜSÜ (tools/marka-cip-kapisi.py'nin kanıtı).

🔴 NEDEN VAR: "kapı yeşil" tek başına bir şey KANITLAMAZ — yeşil, kapının ölçtüğü şeyin
gerçekten kırılabildiğini göstermez. Her eksen için ÖLDÜRÜCÜ bir mutant (kapı KIRMIZI
yanmalı) ve bir KONTROL mutantı (kapı YEŞİL kalmalı) koşulur.

🔴 KABUL `rc` İLE DEĞİL, BEKLENEN İDDİA AİLESİNİN İZİYLE VERİLİR: bir mutant kapıyı
"yanlışlıkla" (başka bir eksenden) kırmızı yakabilir; o tur mutantı ÖLDÜRMÜŞ SAYILMAZ.
Kapının bastığı `DUSEN_AILELER` satırı okunur ve beklenen aile ORADA aranır.

🔴 MUTASYON KOPYAYA UYGULANIR: çalışma ağacı KİRLENMEZ. Geçici ağaç `finally` ve SIGTERM/
SIGINT kancasıyla silinir (sürücü öldürülse bile artık dizin kalmaz).

🔴 İZ ZORUNLU: mutantın GERÇEKTEN uygulandığı, kapının bastığı `IZ=` (ölçülen kaynakların
sha1'i) taban koşumdan FARKLI olmasıyla kanıtlanır. Aynı iz = mutasyon uygulanmadı = o tur
SAYILMAZ ([[mutasyon-bytecode-onbellegi]] · [[mutasyon-kaniti-yeniden-uretilebilir]]).

Kullanım: python3 tools/marka-cip-mutasyon.py
"""
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
_TEMIZLENECEK = []

# (ad, beklenen_aile|None(=YESIL kalmali), dosya, eski, yeni[, kapi])
# `kapi` verilmezse `tools/marka-cip-kapisi.py` koşulur ve kabul `DUSEN_AILELER` izinden
# verilir. Verilirse o kapı koşulur ve kabul, düşen çıktıda `beklenen_aile` dizesinin
# GEÇMESİ ile verilir (yine rc DEĞİL — iz).
MUTANTLAR = [
    ("K1_HEDEF_cipin_hedefi_yok", "HEDEF/cozuldu", "tools/marka_model_build.py",
     'murl = "/marka/" + marka_slug + "/" + g["slug"] + "/"',
     'murl = "/marka/" + marka_slug + "/" + g["slug"] + "-yok/"'),
    ("K2_SAYI_cip_sayisi_sisirildi", "SAYI/filtre", "tools/marka_model_build.py",
     '                       esc(g["display"]), len(g["urunler"])))',
     '                       esc(g["display"]), len(g["urunler"]) + 1))'),
    ("K3_GURULTU_ayri_marka_kolu_kapatildi", "GURULTU/yabanci", "tools/marka_model_build.py",
     '    if g.get("yabanci_marka"):\n        return False',
     '    if False and g.get("yabanci_marka"):\n        return False'),
    ("K4_TIKLAMA_cip_beyani_okunmuyor", "TIKLAMA/aninda", "tools/marka_model_build.py",
     '          var s = cipler[i].querySelector(".adet");',
     '          var s = null;'),
    ("K5_TIKLAMA_on_yukleme_kaldirildi", "TIKLAMA/onyuk", "tools/marka_model_build.py",
     '      cipler[oy].addEventListener("pointerenter", onYukle);\n'
     '      cipler[oy].addEventListener("pointerdown", onYukle);',
     '      cipler[oy].addEventListener("mm-hicbir-zaman", onYukle);'),
    ("K6_KAPSAMA_jeton_sahibi_kolu_kapatildi", "ENVANTER/drift", "tools/marka_model_build.py",
     '            or (sahip is not None and sahip == _canon(marka)))',
     '            or (sahip is not None and sahip == _canon(marka) and False))'),
    ("K7_TIKLAMA_iskelet_cizilmiyor", "TIKLAMA/ekran_dolu", "tools/marka_model_build.py",
     '      if(ix !== null){ iskeletCiz(beyan); }',
     '      if(false){ iskeletCiz(beyan); }'),
    ("K8_BEYAN_baslik_tazelenmiyor", "BEYAN/aninda", "tools/marka_model_build.py",
     '      beyaniYaz(beyan);\n      if(ix !== null)',
     '      if(false){ beyaniYaz(beyan); }\n      if(ix !== null)'),
    # 🔴 KARDEŞ KAPININ SENTETİK FİKSTÜRÜ HÂLÂ KENDİ SINIFINI YAKALIYOR MU (KraL şartı 3b):
    # fikstür 12 Ağu'da değişti (negatif vaka `Zumbaq`ın jeton sahibi başka markaya çekildi).
    # Bu mutant `yayimlanir_mi`den BAŞLIK YARGISI kolunu tamamen siler — yani "yargısız kova
    # sessizce sayfa açar" hâlini geri getirir. Fikstür bunu HÂLÂ yakalamalı ve düşen satırda
    # `Zumbaq` GEÇMELİ; geçmiyorsa fikstür ölmüştür ve kapsama oradan açılamaz.
    ("K9_FIKSTUR_yargisiz_kova_sayfa_aciyor", "Zumbaq", "tools/marka_model_build.py",
     '    if g.get("baslik_dogan") and not baslik_yargisi_var_mi(',
     '    if False and g.get("baslik_dogan") and not baslik_yargisi_var_mi(',
     "tools/model-uyelik-kapisi.py"),
    # KONTROL: GERÇEK bir sayfa metnini değiştirir (üretilen HTML BAYT olarak değişir) ama
    # kapının ölçtüğü dört eksenin HİÇBİRİNE dokunmaz -> kapı YEŞİL kalmalı. Kontrol
    # olmasaydı "her düzenlemede kırmızı yanan" bir kapı da 5/5 mutant öldürmüş görünürdü.
    ("KONTROL_sayfa_metni_degisti", None, "tools/marka_model_build.py",
     'esc("Model filtresini temizle")',
     'esc("Model filtresini kaldır")'),
]

IZ_RE = re.compile(r"^IZ=(\S+)", re.M)
AILE_RE = re.compile(r"^DUSEN_AILELER=(.*)$", re.M)
HUKUM_RE = re.compile(r"^HUKUM=(\S+)", re.M)


def _temizle(*_a):
    for y in list(_TEMIZLENECEK):
        shutil.rmtree(y, ignore_errors=True)
    del _TEMIZLENECEK[:]


def _sinyal(sig, _frame):
    _temizle()
    os._exit(128 + sig)


def izlenen_dosyalar():
    """İzlenen dosyalar + `tools/` altındaki HENÜZ COMMIT EDİLMEMİŞ (ama gitignore'da
    OLMAYAN) dosyalar. İkinci kol olmasaydı sürücü, kendisiyle birlikte yeni yazılmış bir
    kapıyı kopyaya ALMAZ ve taban koşum "dosya yok" diye ÖLÇÜLEMEDİ derdi — commit
    öncesi/sonrası aynı sonucu vermesi kanıtın yeniden üretilebilirliğinin şartıdır."""
    cp = subprocess.run(["git", "-C", KOK, "ls-files"], capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit("OLCULEMEDI: git ls-files başarısız (%s)" % cp.stderr[-200:])
    dosyalar = [x for x in cp.stdout.splitlines() if x.strip()]
    ek = subprocess.run(["git", "-C", KOK, "ls-files", "--others", "--exclude-standard",
                         "tools"], capture_output=True, text=True)
    if ek.returncode == 0:
        dosyalar += [x for x in ek.stdout.splitlines() if x.strip()]
    return sorted(set(dosyalar))


def agac_kur(dosyalar):
    tmp = tempfile.mkdtemp(prefix="mm-cip-mut-")
    _TEMIZLENECEK.append(tmp)
    for rel in dosyalar:
        kaynak = os.path.join(KOK, rel)
        if not os.path.isfile(kaynak):
            continue
        hedef = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copy2(kaynak, hedef)
    return tmp


def kapiyi_kos(agac, kapi_yolu="tools/marka-cip-kapisi.py"):
    cp = subprocess.run([sys.executable, os.path.join(agac, *kapi_yolu.split("/"))],
                        cwd=agac, capture_output=True, text=True, timeout=3600)
    ciktı = cp.stdout + "\n" + cp.stderr
    iz = IZ_RE.search(ciktı)
    aile = AILE_RE.search(ciktı)
    hukum = HUKUM_RE.search(ciktı)
    return {"rc": cp.returncode,
            "iz": iz.group(1) if iz else None,
            "aileler": set(x for x in (aile.group(1).split(",") if aile else []) if x != "-"),
            "hukum": hukum.group(1) if hukum else "YOK",
            "ham": ciktı}


def main():
    signal.signal(signal.SIGTERM, _sinyal)
    signal.signal(signal.SIGINT, _sinyal)
    dosyalar = izlenen_dosyalar()
    try:
        taban_agac = agac_kur(dosyalar)
        taban = kapiyi_kos(taban_agac)
        shutil.rmtree(taban_agac, ignore_errors=True)
        _TEMIZLENECEK.remove(taban_agac)
        print("TABAN: hukum=%s iz=%s" % (taban["hukum"], taban["iz"]), flush=True)
        if taban["hukum"] != "YESIL":
            print("OLCULEMEDI: taban koşum YEŞİL değil — mutasyon yargısı kurulamaz")
            return 3

        olduren, bekleyen, kontrol_sonuc = 0, 0, None
        for kayit in MUTANTLAR:
            ad, beklenen, rel, eski, yeni = kayit[:5]
            kapi_yolu = kayit[5] if len(kayit) > 5 else "tools/marka-cip-kapisi.py"
            agac = agac_kur(dosyalar)
            yol = os.path.join(agac, rel)
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if metin.count(eski) != 1:
                print("OLCULEMEDI: %s çapası %d kez bulundu (1 bekleniyor)"
                      % (ad, metin.count(eski)))
                shutil.rmtree(agac, ignore_errors=True)
                return 3
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni))
            s = kapiyi_kos(agac, kapi_yolu)
            if kapi_yolu != "tools/marka-cip-kapisi.py":
                # Yabancı kapının kendi `IZ=` satırı yok -> mutasyonun UYGULANDIĞINI dosya
                # içeriğinden kanıtla (aynı disiplin: iz DEĞİŞMEDİYSE tur SAYILMAZ).
                with open(yol, encoding="utf-8") as f:
                    s["iz"] = "yabanci:%s" % (yeni in f.read())
            shutil.rmtree(agac, ignore_errors=True)
            _TEMIZLENECEK.remove(agac)
            if kapi_yolu != "tools/marka-cip-kapisi.py":
                if s["iz"] != "yabanci:True":
                    print("OLCULEMEDI: %s mutasyonu dosyaya YAZILMADI — tur SAYILMAZ" % ad)
                    return 3
                bekleyen += 1
                oldu = (s["rc"] != 0 and beklenen in s["ham"])
                olduren += 1 if oldu else 0
                print("  %-42s rc=%-3s iz=%-16s -> %s"
                      % (ad, s["rc"], beklenen, "OLDU" if oldu else "KACTI"), flush=True)
                if not oldu:
                    print("      (kapi=%s rc=%s; beklenen iz '%s' ciktida YOK)"
                          % (kapi_yolu, s["rc"], beklenen))
                continue
            if s["iz"] is None or s["iz"] == taban["iz"]:
                print("OLCULEMEDI: %s izi DEĞİŞMEDİ (mutasyon uygulanmadı) — tur SAYILMAZ" % ad)
                return 3
            if beklenen is None:
                kontrol_sonuc = s["hukum"]
                print("  KONTROL %-40s hukum=%s  (YESIL bekleniyor)" % (ad, s["hukum"]),
                      flush=True)
                continue
            bekleyen += 1
            oldu = beklenen in s["aileler"]
            olduren += 1 if oldu else 0
            print("  %-42s hukum=%-8s aile=%-16s -> %s"
                  % (ad, s["hukum"], beklenen, "OLDU" if oldu else "KACTI"), flush=True)
            if not oldu:
                print("      DUSEN_AILELER=%s" % (",".join(sorted(s["aileler"])) or "-"))
        print("MUTANT=%d/%d KONTROL=%s"
              % (olduren, bekleyen, "YESIL" if kontrol_sonuc == "YESIL" else "KIRMIZI"))
        # 🔴 İZ AYRIMI: her öldürücü mutant BEKLENEN aileden düştü mü + kontrol yeşil kaldı mı
        iz_ayrimi = (olduren == bekleyen and kontrol_sonuc == "YESIL")
        print("IZ_AYRIMI=%s" % ("DOGRU" if iz_ayrimi else "YANLIS"))
        return 0 if iz_ayrimi else 1
    finally:
        _temizle()


if __name__ == "__main__":
    sys.exit(main())
