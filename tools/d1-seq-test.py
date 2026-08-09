#!/usr/bin/env python3
"""D1 seq nobetcisi: tam sayi + kanonik katalog sirasi, offline kontrol mutanti."""
import importlib.util
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, "tools", "d1-sync.py")
spec = importlib.util.spec_from_file_location("d1_sync_seq", YOL)
m = importlib.util.module_from_spec(spec)
sys.modules["d1_sync_seq"] = m
spec.loader.exec_module(m)

urunler = [{"id": "yeni"}, {"id": "orta"}, {"id": "eski"}]
gecen = 0
kalan = 0


def dogrula(ad, kosul, detay=""):
    global gecen, kalan
    if kosul:
        gecen += 1
        print("GECTI " + ad)
    else:
        kalan += 1
        print("KALDI " + ad + (" — " + detay if detay else ""))


hedef = m.seq_hedefleri(urunler)
dogrula("kanonik hedeflerin hepsi tam sayi", all(isinstance(v, int) for v in hedef.values()))
dogrula("kanonik hedef sirasinda kati azalan", hedef["yeni"] > hedef["orta"] > hedef["eski"])

kesirli, sapan, _ = m.seq_sira_hali(urunler, hedef)
dogrula("temiz kontrol YESIL", not kesirli and not sapan, "kesirli=%s sapan=%s" % (kesirli, sapan))

# KONTROL MUTANTI: sirayi bozmadan tek kesirli seq enjekte edilir. Yalniz ORDER BY
# kontrol eden bir nobetci bunu kacirir; tam-sayi iddiasi mutlaka KIRMIZI yakmalidir.
mutant = dict(hedef)
mutant["orta"] = hedef["orta"] + 0.5
kesirli_m, sapan_m, _ = m.seq_sira_hali(urunler, mutant)
dogrula("KONTROL MUTANTI: kesirli seq KIRMIZI yakti", kesirli_m == ["orta"] and not sapan_m,
        "kesirli=%s sapan=%s" % (kesirli_m, sapan_m))

# Ikinci mutant tam sayidir ama iki urunun sirasi ters: monotonluk ayagi yakalamalidir.
mutant2 = dict(hedef)
mutant2["yeni"], mutant2["orta"] = mutant2["orta"], mutant2["yeni"]
kesirli_2, sapan_2, _ = m.seq_sira_hali(urunler, mutant2)
dogrula("SIRA MUTANTI: kanonik siradan sapma KIRMIZI yakti",
        not kesirli_2 and len(sapan_2) == 2, str(sapan_2))


def urun(uid):
    return {"id": uid, "baslik": uid, "kategori": "Oyun/Hobi", "marka": [],
            "fiyat": "100 TL", "gorseller": [], "aciklama": uid}


# KOK NEDEN YAZICI AYAGI: mid-array urun genis araliga TAM SAYI girer; bitisik legacy
# aralikta eski kesir davranisina donmez, fail-loud normalizasyon ister.
u3, un, u2, u1 = urun("u3"), urun("un"), urun("u2"), urun("u1")
mevcut = {u["id"]: (m.arama.urun_hash(u), "") for u in (u3, u2, u1)}
_yeni, _degisen, _baski, _silinen, _gorulen = m.diff_plan(
    [u3, un, u2, u1], mevcut, {}, False, 3000000,
    {"u3": 3000000, "u2": 2000000, "u1": 1000000})
dogrula("mid-array yazici kesir degil tam-sayi orta nokta uretir",
        len(_yeni) == 1 and "2500000" in _yeni[0] and ".0" not in _yeni[0],
        str(_yeni))

try:
    m.diff_plan([u3, un, u2, u1], mevcut, {}, False, 3,
                {"u3": 3, "u2": 2, "u1": 1})
    _fail_loud = False
except SystemExit as e:
    _fail_loud = "--seq-normalize" in str(e.code)
dogrula("bitisik aralik kesir uretmek yerine fail-loud durur", _fail_loud)

print("SONUC: %d gecti, %d kaldi" % (gecen, kalan))
sys.exit(0 if kalan == 0 else 1)
