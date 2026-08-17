#!/usr/bin/env python3
"""D1 seq nobetcisi: tam sayi + kanonik katalog sirasi, offline kontrol mutanti."""
import importlib.util
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, "tools", "d1-sync.py")
spec = importlib.util.spec_from_file_location("d1_sync_seq", YOL)
m = importlib.util.module_from_spec(spec)
sys.modules["d1_sync_seq"] = m
spec.loader.exec_module(m)

SEQ_ADIM = m.SEQ_ADIM
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


# ═════════════════════════════════════════════════════════════════════════════
# ON KONTROLLER (regresyon)
# ═════════════════════════════════════════════════════════════════════════════
urunler = [{"id": "yeni"}, {"id": "orta"}, {"id": "eski"}]
hedef = m.seq_hedefleri(urunler)
dogrula("kanonik hedeflerin hepsi tam sayi", all(isinstance(v, int) for v in hedef.values()))
dogrula("kanonik hedef sirasinda kati azalan", hedef["yeni"] > hedef["orta"] > hedef["eski"])

kesirli, sapan, _ = m.seq_sira_hali(urunler, hedef)
dogrula("temiz kontrol YESIL", not kesirli and not sapan, "kesirli=%s sapan=%s" % (kesirli, sapan))

# KONTROL MUTANTI: sirayi bozmadan tek kesirli seq enjekte edilir.
mutant = dict(hedef)
mutant["orta"] = hedef["orta"] + 0.5
kesirli_m, sapan_m, _ = m.seq_sira_hali(urunler, mutant)
dogrula("KONTROL MUTANTI: kesirli seq KIRMIZI yakti", kesirli_m == ["orta"] and not sapan_m,
        "kesirli=%s sapan=%s" % (kesirli_m, sapan_m))

# SIRA MUTANTI: tam sayidir ama iki urunun sirasi ters.
mutant2 = dict(hedef)
mutant2["yeni"], mutant2["orta"] = mutant2["orta"], mutant2["yeni"]
kesirli_2, sapan_2, _ = m.seq_sira_hali(urunler, mutant2)
dogrula("SIRA MUTANTI: kanonik siradan sapma KIRMIZI yakti",
        not kesirli_2 and len(sapan_2) == 2, str(sapan_2))


def urun(uid):
    return {"id": uid, "baslik": uid, "kategori": "Oyun/Hobi", "marka": [],
            "fiyat": "100 TL", "gorseller": [], "aciklama": uid}


def mevcut_dict(urunler):
    return {u["id"]: (m.arama.urun_hash(u), "") for u in urunler}


# ═════════════════════════════════════════════════════════════════════════════
# VAKALAR
# ═════════════════════════════════════════════════════════════════════════════

# V1: tek bosluga 26 ardisik yeni id, bosluk = SEQ_ADIM.
# Ikili bolme bu vakada ~20 adimda tukenirdi; blok-oranli cozum hepsini ayri tam sayi verir.
head, tail = urun("v1-head"), urun("v1-tail")
v1_yeni = [urun("v1-y%02d" % i) for i in range(26)]
v1_urunler = [head] + v1_yeni + [tail]
v1_mevcut_seq = {head["id"]: 2 * SEQ_ADIM, tail["id"]: 1 * SEQ_ADIM}
v1_mevcut = mevcut_dict([head, tail])
v1_yeni_sql, _, _, _, _ = m.diff_plan(
    v1_urunler, v1_mevcut, {}, False, 0, v1_mevcut_seq)
v1_seqs = [int(re.search(r"\([^,]+,[^,]+,(\d+)", s).group(1)) for s in v1_yeni_sql]
dogrula("V1 26 ardisik yeni id tam sayi/farkli/monoton/alt-ust arasinda",
        len(v1_seqs) == 26 and
        all(isinstance(x, int) for x in v1_seqs) and
        len(set(v1_seqs)) == 26 and
        v1_seqs == sorted(v1_seqs) and
        all(SEQ_ADIM < x < 2 * SEQ_ADIM for x in v1_seqs),
        "seqs=%s" % v1_seqs)

# V2: ayni vaka ama bosluk GERCEKTEN dar (adim < 1) -> fail-loud AYNEN.
head2, tail2 = urun("v2-head"), urun("v2-tail")
v2_yeni = [urun("v2-y%02d" % i) for i in range(26)]
v2_urunler = [head2] + v2_yeni + [tail2]
v2_mevcut_seq = {head2["id"]: 30, tail2["id"]: 4}   # bosluk = 26 < 26+1
v2_mevcut = mevcut_dict([head2, tail2])
try:
    m.diff_plan(v2_urunler, v2_mevcut, {}, False, 0, v2_mevcut_seq)
    v2_fail = False
    v2_msg = ""
except SystemExit as e:
    v2_fail = True
    v2_msg = str(e.code)
dogrula("V2 dar bosluk fail-loud AYNEN",
        v2_fail and "SEQ TAM SAYI ARALIGI TUKENDI" in v2_msg and "k=" in v2_msg,
        v2_msg)

# V3: tek bosluga 1 yeni id -> bugunku sonucla AYNI (regresyon).
u3, un, u2, u1 = urun("u3"), urun("un"), urun("u2"), urun("u1")
v3_mevcut = mevcut_dict([u3, u2, u1])
v3_yeni, _, _, _, _ = m.diff_plan(
    [u3, un, u2, u1], v3_mevcut, {}, False, 3000000,
    {"u3": 3000000, "u2": 2000000, "u1": 1000000})
dogrula("V3 tek yeni id tam-sayi orta nokta uretir",
        len(v3_yeni) == 1 and "2500000" in v3_yeni[0] and ".0" not in v3_yeni[0],
        str(v3_yeni))

# V4: kuyruk blogu -> AYNEN calisir.
head4 = urun("v4-head")
v4_yeni = [urun("v4-y%d" % i) for i in range(3)]
v4_urunler = [head4] + v4_yeni
v4_mevcut_seq = {head4["id"]: SEQ_ADIM}
v4_mevcut = mevcut_dict([head4])
v4_yeni_sql, _, _, _, _ = m.diff_plan(
    v4_urunler, v4_mevcut, {}, False, 0, v4_mevcut_seq)
v4_seqs = [int(re.search(r"\([^,]+,[^,]+,(\d+)", s).group(1)) for s in v4_yeni_sql]
dogrula("V4 kuyruk blogu tam sayi/farkli/monoton/0-ust arasinda",
        len(v4_seqs) == 3 and
        all(isinstance(x, int) for x in v4_seqs) and
        len(set(v4_seqs)) == 3 and
        v4_seqs == sorted(v4_seqs) and
        all(0 < x < SEQ_ADIM for x in v4_seqs),
        "seqs=%s" % v4_seqs)

# V5: plan BOS + sandvic -> yeni mesaj basilir, "normalize kos" DEMEZ, k= icerir.
# Gercek diff_plan'da plan bosken fail-loud tetiklemek matematiksel olarak mumkun degil;
# mesaj secimi dogrudan _seq_fail_loud uzerinden olculur.
a5, y5, b5 = urun("v5-a"), urun("v5-y"), urun("v5-b")
v5_urunler = [a5, y5, b5]
v5_mevcut_seq = {a5["id"]: 3 * SEQ_ADIM, b5["id"]: 1 * SEQ_ADIM}  # kanonik, normalize plani BOS
try:
    m._seq_fail_loud(y5["id"], 1, 2, 1, v5_urunler, v5_mevcut_seq)
    v5_fail = False
    v5_msg = ""
except SystemExit as e:
    v5_fail = True
    v5_msg = str(e.code)
dogrula("V5 plan bos sandvic yeni mesaj (normalize onerisi yok, k= var)",
        v5_fail and "bosluk zaten kanonik" in v5_msg and "k=" in v5_msg and
        "--seq-normalize" not in v5_msg,
        v5_msg)

print("SONUC: %d gecti, %d kaldi" % (gecen, kalan))
sys.exit(0 if kalan == 0 else 1)
