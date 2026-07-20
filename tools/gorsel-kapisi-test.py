#!/usr/bin/env python3
"""gorsel-kapisi-test.py — gorsel_mukerrer_kapisi.py KABUL TESTI.

Sentetik PNG'lerle (gercek R2/ag YOK) kapinin dogru ayrimi:
  - birebir ayni foto  -> MUKERRER (hamming 0)
  - hafif varyant       -> MUKERRER (hamming <= esik)  [yeniden-sikistirma/parlaklik]
  - tamamen farkli      -> GECER    (hamming > esik)   [yanlis-pozitif olcumu]
  - backfill senaryosu  -> aday, YAYINDAKI gorselin ikizi ise elenir; farkli gecer (defect d)

RED-MUTASYON: esigi 0'a dus -> varyant artik ikiz sayilmaz -> ilgili assert KIRMIZI olmali.
Bunu bu betik CANLI dogrular: DHASH_ESIK'i 0 alarak filtrele cagirir, varyantin GECMESI
gerektigini (yani kapinin bozuldugunu) teyit eder. Boylece nobetin gercekten koruma yaptigi
ispatlanir; ana esik (12) ile varyant ELENIR.
"""
import importlib.util
import os
import sys
import tempfile

ROOT = "/Users/okan/dev/pruvo"
# worktree'de de calissin diye betigin kendi dizininden yukle:
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "gmk", os.path.join(HERE, "gorsel_mukerrer_kapisi.py"))
gmk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gmk)

try:
    from PIL import Image
except ImportError:
    print("PIL YOK -> kabul testi CALISTIRILAMADI (Pillow gerekli).", file=sys.stderr)
    sys.exit(2)

W = H = 128


def _kaydet(px, path):
    im = Image.new("L", (W, H))
    im.putdata(px)
    im.save(path)


def _base():
    """Yatay parlaklik gradyani + birkac blok -> yapisal, ayirt edici bir dHash."""
    px = []
    for y in range(H):
        for x in range(W):
            v = int(x / W * 200) + 20
            if 30 < x < 60 and 30 < y < 90:
                v = 240
            if 80 < x < 110 and 40 < y < 100:
                v = 15
            px.append(max(0, min(255, v)))
    return px


def _varyant(px):
    """Ayni foto, hafif isleme: parlaklik +12 + hucre bazli kucuk gurultu.
    dHash yatay komsu-fark yapisi KORUNUR -> kucuk hamming."""
    out = []
    for i, v in enumerate(px):
        n = (i * 37) % 7 - 3          # -3..+3 deterministik kucuk gurultu
        out.append(max(0, min(255, v + 12 + n)))
    return out


def _farkli_dikey():
    """DIKEY gradyan (base yataydi) -> yatay komsu-fark bitleri cok farkli -> buyuk hamming."""
    px = []
    for y in range(H):
        for x in range(W):
            v = int(y / H * 200) + 20
            if 40 < y < 70 and 20 < x < 100:
                v = 250
            px.append(max(0, min(255, v)))
    return px


def _farkli_dama():
    """Dama deseni -> base'in gradyaniyla alakasiz -> buyuk hamming."""
    px = []
    for y in range(H):
        for x in range(W):
            px.append(240 if ((x // 8) + (y // 8)) % 2 == 0 else 15)
    return px


def main():
    tmp = tempfile.mkdtemp(prefix="gkapi-test-")
    p_base = os.path.join(tmp, "base.png")
    p_ayni = os.path.join(tmp, "ayni.png")       # birebir ayni pikseller
    p_var = os.path.join(tmp, "varyant.png")
    p_dik = os.path.join(tmp, "farkli_dikey.png")
    p_dama = os.path.join(tmp, "farkli_dama.png")

    base = _base()
    _kaydet(base, p_base)
    _kaydet(base, p_ayni)                          # ayni veri, farkli DOSYA (string != gorsel)
    _kaydet(_varyant(base), p_var)
    _kaydet(_farkli_dikey(), p_dik)
    _kaydet(_farkli_dama(), p_dama)

    hb = gmk.dhash(p_base)
    ha = gmk.dhash(p_ayni)
    hv = gmk.dhash(p_var)
    hd = gmk.dhash(p_dik)
    hdm = gmk.dhash(p_dama)

    d_ayni = gmk.hamming(hb, ha)
    d_var = gmk.hamming(hb, hv)
    d_dik = gmk.hamming(hb, hd)
    d_dama = gmk.hamming(hb, hdm)
    E = gmk.DHASH_ESIK

    print("=== olculen hamming (256 bit, esik=%d) ===" % E)
    print("  base~ayni(birebir) : %d" % d_ayni)
    print("  base~varyant       : %d" % d_var)
    print("  base~farkli_dikey  : %d" % d_dik)
    print("  base~farkli_dama   : %d" % d_dama)

    hata = []

    # 1) birebir ayni foto -> hamming 0 -> MUKERRER
    if d_ayni != 0:
        hata.append("birebir ayni foto hamming!=0 (%d)" % d_ayni)
    if not gmk.mukerrer_mi(ha, [hb])[0]:
        hata.append("birebir ayni foto MUKERRER sayilmadi")

    # 2) hafif varyant -> 0 < hamming <= esik -> MUKERRER
    if not (0 < d_var <= E):
        hata.append("varyant hamming beklenen (0,%d] disinda: %d" % (E, d_var))
    if not gmk.mukerrer_mi(hv, [hb])[0]:
        hata.append("hafif varyant MUKERRER sayilmadi (hamming=%d)" % d_var)

    # 3) tamamen farkli -> hamming > esik -> GECER (yanlis-pozitif olcumu)
    if d_dik <= E:
        hata.append("farkli_dikey yanlislikla ikiz (hamming=%d<=%d)" % (d_dik, E))
    if d_dama <= E:
        hata.append("farkli_dama yanlislikla ikiz (hamming=%d<=%d)" % (d_dama, E))
    if gmk.mukerrer_mi(hd, [hb])[0]:
        hata.append("farkli_dikey MUKERRER sayildi (yanlis pozitif)")

    # 4) filtrele (aday-ici): [base, ayni, varyant, dikey, dama]
    #    beklenen gecen = base + dikey + dama ; elenen = ayni + varyant
    s = gmk.filtrele([p_base, p_ayni, p_var, p_dik, p_dama])
    gecen = set(os.path.basename(x) for x in s["gecen"])
    elenen = set(os.path.basename(e["aday"]) for e in s["elenen"])
    if gecen != {"base.png", "farkli_dikey.png", "farkli_dama.png"}:
        hata.append("filtrele gecen yanlis: %s" % sorted(gecen))
    if elenen != {"ayni.png", "varyant.png"}:
        hata.append("filtrele elenen yanlis: %s" % sorted(elenen))

    # 5) BACKFILL senaryosu (defect d): aday YAYINDAKI gorselin ikizi ise elenmeli.
    #    yayin=[base]; aday=[varyant(ikiz), farkli_dama(yeni)] -> varyant ELE, dama GEC.
    sb = gmk.filtrele([p_var, p_dama], mevcut_yollar=[p_base])
    gb = set(os.path.basename(x) for x in sb["gecen"])
    eb = set(os.path.basename(e["aday"]) for e in sb["elenen"])
    kaynaklar = set(e["kaynak"] for e in sb["elenen"])
    if gb != {"farkli_dama.png"}:
        hata.append("backfill gecen yanlis: %s (yeni gorsel gecmeli)" % sorted(gb))
    if eb != {"varyant.png"}:
        hata.append("backfill elenen yanlis: %s (yayin ikizi elenmeli)" % sorted(eb))
    if eb and kaynaklar != {"yayin"}:
        hata.append("backfill ikiz kaynagi 'yayin' degil: %s" % kaynaklar)

    # 6) YANLIS-POZITIF olcumu: sirf farkli gorseller -> HICBIRI elenmemeli
    s6 = gmk.filtrele([p_base, p_dik, p_dama])
    if s6["elenen"]:
        hata.append("yanlis pozitif: farkli gorseller elendi -> %s"
                    % [os.path.basename(e["aday"]) for e in s6["elenen"]])

    # 7b) EKLEME HATTI SARMALAYICI (secili_temizle): ekle scriptlerinin cagirdigi yol.
    #     cache dizinindeki secili DOSYA ADLARINI arindirir, SIRAYI korur, dosya adi doner.
    #     base + ayni + varyant + dama -> temiz = [base, dama]; sira korunur.
    import shutil
    cdir = os.path.join(tmp, "cache")
    os.makedirs(cdir, exist_ok=True)
    for src, ad in [(p_base, "g1.jpg"), (p_ayni, "g2.jpg"), (p_var, "g3.jpg"), (p_dama, "g4.jpg")]:
        shutil.copy(src, os.path.join(cdir, ad))
    temiz, res = gmk.secili_temizle(cdir, ["g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg"])
    if temiz != ["g1.jpg", "g4.jpg"]:
        hata.append("secili_temizle temiz yanlis: %s (beklenen g1,g4; sira korunmali)" % temiz)
    if res.get("pil_yok"):
        hata.append("secili_temizle pil_yok True dondu (PIL var olmali)")

    # 7) RED-MUTASYON CANLI ISPAT: esik=0 iken varyant artik ikiz DEGIL (kapi korumasiz).
    #    Bu, ana esik(12) korumasinin gercek oldugunu -- esige bagli oldugunu -- kanitlar.
    s0 = gmk.filtrele([p_var], mevcut_yollar=[p_base], esik=0)
    if not s0["gecen"] or s0["elenen"]:
        hata.append("red-mutasyon beklentisi tutmadi: esik=0'da varyant hala ikiz sayildi")
    else:
        print("RED-MUTASYON ISPAT: esik=0 -> varyant GECTI (koruma esige bagli, dogru).")

    print("-" * 60)
    if hata:
        print("KIRMIZI (%d):" % len(hata))
        for h in hata:
            print("  ✘", h)
        return 1
    print("YESIL: kabul kosullari gecti (birebir+varyant ele, farkli gecer, backfill + hatti-sarmalayici + yanlis-pozitif dogru).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
