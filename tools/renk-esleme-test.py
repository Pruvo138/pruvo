#!/usr/bin/env python3
"""KABUL: RENK ESLEME KAPISI (BaBa 8 Eki 15:5x) — "ucret alinan her ek renk uretime BAGLI olmali".

NEDEN: bust paletten 1-2 renk sattiriyordu (2. renk +100 TL) ama esle_bust renkleri hic okumuyordu (uretim varsayilan
tek renk); logo tabani "Yok" / ses basligi bos iken secilen farkli renk de ucretleniyor ama uretilmiyordu. Sinif:
fiyata giren renk (VERI.renkBolgesiAktif, sunucu) ile uretece giden renk (esle_<kod> ciktisi + donen bolge listesi =
olcu.json parcalari) AYRISIRSA musteri basilmayan renge oder.

HERMETIK (CI'da kosar; node + bu agacin manifesti + tools/foto-uretec-kosucu.py; uretec deposu GEREKMEZ):
  her renk bolgeli tur (ESLEMELER'de; palet turu bust dahil) icin dogrulanmis ornek parametre
  (kopru-esle-kapisi-test.s_katmani) + her bolgeye FARKLI renk:
  A1 AKTIF   koşul acik (renk_kosul degerler[0] / dolu "PRUVO"): her bolge VERI'de aktif VE esle donus listesinde VE
             renginin hex'i esle ciktisinda (renk_* alanina gitti)
  A2 PASIF   koşul kapali: VERI pasif der ise esle de o bolgeyi URETMEZ (donus listesinde yok) — ve tersi
  A3 PALET   bust 2 renk -> taban + rolyef hex'leri ciktida, iki_renk true; 1 renk -> yalniz taban, iki_renk false
  LITOFAN    ayri yol (esle yok): renk uretece GITMEZ, olcu.json parcalarina (panel/ayak) yazilir; ayak koşulsuz
             (`--ayak 1`) -> kaynak olcumu (bolgeler kosulsuz + parcalar renk adini tasir)
MUTANTLAR (gecici kopyada; calisma agacina YAZMAZ):
  MR1 esle_bust iki_renk/bolge eslemesi silindi -> A3 · MR2 esle_qr renk_qr dustu -> A1 qr
  MR3 manifest logo renk_kosul silindi -> A2 logo (GIZLI-KOSUL: taban "Yok" iken uretilmiyor)
  MR5 uretim esle secimi uretece dondu (tekin_kos bust icin esle_rolyef kosar) -> A3 bust (8 Eki yerel 3MF bulgusu) · MR4 esle_ses "yazi" donusu silindi -> A1 ses
  MR0 kontrol: yorum eklendi -> 0 kirmizi
Cikti: `RENK_ESLEME <bagli>/<toplam> tur` + son satir `VAKA_KIRMIZI=<n> SURVIVOR=<n>` (rc 0 yalniz ikisi de 0)
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSUCU = os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
MANIFEST = os.path.join(KOK, "foto-uretim-veri.js")

NODE_AKTIF = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "const V=k.PRUVO_FOTO;const q=JSON.parse(fs.readFileSync(0,'utf8'));"
    "process.stdout.write(JSON.stringify(q.map((x)=>V.renkBolgesiAktif(x[0],x[1],x[2]))));"
)


def modul(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


ESLE = modul("kopru_esle_kapisi_test", os.path.join(KOK, "tools", "kopru-esle-kapisi-test.py"))


def aktif_mi(manifest, sorgu):
    if not sorgu:
        return []
    p = subprocess.run(["node", "-e", NODE_AKTIF, manifest], input=json.dumps(sorgu), capture_output=True, text=True,
                       timeout=60)
    if p.returncode != 0:
        raise SystemExit("node: " + p.stderr.strip()[:300])
    return json.loads(p.stdout)


def _hexler(u):
    cikti = set()
    for v in u.values():
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", x):
                cikti.add(x.upper())
    return cikti


def _kosul_degeri(c, ac, form):
    """Koşulu ACAN (ac=True) ya da KAPATAN deger."""
    if c.get("dolu") is True:
        return "PRUVO" if ac else ""
    d = c.get("degerler") or []
    if ac:
        return d[0]
    sec = [x for x in ((form.get(c.get("alan")) or {}).get("secenekler") or []) if x not in d]
    if sec:
        return sec[0]
    return (not d[0]) if isinstance(d[0], bool) else None


def kapi(kosucu_yol, manifest):
    """-> (kirmizi, {tur: bagli_mi}, litofan_notu)."""
    kos = modul("kosucu_renk_%d" % abs(hash(kosucu_yol)), kosucu_yol)
    turler = {t.get("kod"): t for t in ESLE.node(manifest) if isinstance(t, dict)}
    rh = kos.renk_tablosu()
    adlar, gor = [], set()
    for ad, hx in rh.items():
        if hx.upper() not in gor:
            gor.add(hx.upper())
            adlar.append(ad)
    kodlar = sorted(k for k in kos.ESLEMELER if k in turler and
                    ((turler[k].get("renk_bolgeleri") or []) or (turler[k].get("palet_bolgeleri") or [])))
    sk, deger, _ = ESLE.s_katmani(manifest, kodlar)
    kirmizi = [k for k in sk if k.startswith(("SUNUCU", "ORNEK"))]
    tablo = {}
    for kod in kodlar:
        t = turler[kod]
        form = t.get("form") or {}
        palet = list(t.get("palet_bolgeleri") or [])
        bolgeler = palet or [b["kod"] for b in t.get("renk_bolgeleri") or []]
        renk = {b: adlar[i % len(adlar)] for i, b in enumerate(bolgeler)}
        kosul = t.get("renk_kosul") or {}
        ok = True

        def kos_esle(p, r):
            d = tempfile.mkdtemp(prefix="renk-esleme-")
            try:
                # Ust sinir olcusu: isimlik kisa kenari (ornek) uzun kenari asmasin (kisa-kenar RED'i olcu disi).
                g = {"tur": kod, "olcu_mm": (t.get("olcu_mm") or {}).get("en_cok") or 100, "parametreler": p,
                     "dosyalar": ESLE._dosyalar(d), "renkler": r}
                # URETIM YOLUNUN secimi (tekin_kos ile ayni nokta): bust rolyef_uret kosar ama esle_bust baglar.
                return kos.esle_fonksiyonu(t, kos.cli_tablosu().get(t.get("uretec")))(g, d, rh)
            finally:
                shutil.rmtree(d, ignore_errors=True)

        # A1 AKTIF: tum koşullar acik.
        p_ac = dict(deger.get(kod) or {})
        for b, cl in kosul.items():
            for c in cl:
                p_ac[c["alan"]] = _kosul_degeri(c, True, form)
        try:
            u, don = kos_esle(p_ac, renk)
        except kos.KopruRed as e:
            kirmizi.append("A1 KOPRU-RED %s=%s" % (kod, e.kod))
            tablo[kod] = False
            continue
        akt = aktif_mi(manifest, [[kod, b, p_ac] for b in bolgeler]) if not palet else [True] * len(bolgeler)
        hx = _hexler(u)
        for b, a in zip(bolgeler, akt):
            if not a:
                kirmizi.append("A1 VERI-PASIF %s.%s (koşul acikken)" % (kod, b))
                ok = False
            elif b not in don:
                kirmizi.append("A1 URETILMEZ %s.%s (esle donus listesinde yok)" % (kod, b))
                ok = False
            elif rh[renk[b]].upper() not in hx:
                kirmizi.append("A1 RENK-GITMEZ %s.%s (%s ciktida yok)" % (kod, b, renk[b]))
                ok = False
        if palet:
            # A3 PALET: 2 renk -> iki_renk true; 1 renk -> yalniz ilk bolge, iki_renk false.
            if u.get("iki_renk") is not True:
                kirmizi.append("A3 PALET %s iki renk odendi, iki_renk=%r" % (kod, u.get("iki_renk")))
                ok = False
            u1, d1 = kos_esle(p_ac, {palet[0]: renk[palet[0]]})
            if u1.get("iki_renk") is not False or d1 != palet[:1]:
                kirmizi.append("A3 PALET %s tek renk: iki_renk=%r donus=%s" % (kod, u1.get("iki_renk"), d1))
                ok = False
        # A2 PASIF: her koşullu bolge tek tek kapatilir; VERI karari == esle karari.
        for b, cl in kosul.items():
            p_kap = dict(p_ac)
            for c in cl:
                v = _kosul_degeri(c, False, form)
                if v is None:
                    p_kap.pop(c["alan"], None)
                else:
                    p_kap[c["alan"]] = v
            veri = aktif_mi(manifest, [[kod, b, p_kap]])[0]
            try:
                _, don2 = kos_esle(p_kap, renk)
            except kos.KopruRed as e:
                kirmizi.append("A2 KOPRU-RED %s.%s=%s" % (kod, b, e.kod))
                ok = False
                continue
            if veri != (b in don2):
                kirmizi.append("A2 KOSUL-UYUMSUZ %s.%s VERI=%s esle=%s" % (kod, b, veri, b in don2))
                ok = False
        # A2 GIZLI-KOSUL: manifestte koşulsuz bolge, formun HER secim/bool/metin degerinde uretilmeli (esle bir
        # parametreye bagli olarak dusuruyorsa manifest koşulu EKSIK -> pasifken de ucret alinir).
        if not palet:
            for alan, sema in form.items():
                tip = sema.get("tip")
                if tip == "secim":
                    secenek = list(sema.get("secenekler") or [])
                elif tip == "bool":
                    secenek = [True, False]
                elif tip == "metin":
                    secenek = ["", "PRUVO"]
                else:
                    continue
                for v in secenek:
                    p_v = dict(p_ac, **{alan: v})
                    try:
                        _, don_v = kos_esle(p_v, renk)
                    except kos.KopruRed:
                        continue
                    for b in bolgeler:
                        if b not in kosul and b not in don_v:
                            kirmizi.append("A2 GIZLI-KOSUL %s.%s %s=%r iken uretilmiyor (manifestte koşul yok)"
                                           % (kod, b, alan, v))
                            ok = False
        tablo[kod] = ok
    # LITOFAN (esle yok): renk uretece gitmez, olcu.json parcalari; ayak koşulsuz.
    with open(kosucu_yol, encoding="utf-8") as f:
        ks = f.read()
    lt = turler.get("litofan") or {}
    lit_ok = ('"--ayak", "1"' in ks and 'renk.get("panel"' in ks and 'renk.get("ayak"' in ks and
              not (lt.get("renk_kosul") or {}))
    if not lit_ok:
        kirmizi.append("LITOFAN parcalar/ayak koşulsuzlugu olculemedi")
    tablo["litofan"] = lit_ok
    return kirmizi, tablo


MUTANT_KOSUCU = {
    "MR1 esle_bust eslemesi silindi": ('    u["iki_renk"] = "rolyef" in secilen\n', "", r"^A3 PALET bust"),
    "MR2 esle_qr renk_qr dustu": (', renk_qr=_renk(g, "kod", rh))', ")", r"^A1 RENK-GITMEZ qr\.kod"),
    "MR4 esle_ses yazi donusu silindi": ('["plaka", "cubuk"] + (["yazi"] if str(u.get("baslik") or "").strip() else [])',
                                         '["plaka", "cubuk"]', r"^A1 URETILMEZ ses\.yazi"),
    "MR5 uretim esle secimi uretece dondu (tur onceligi silindi)": (
        'return ESLEMELER.get((t or {}).get("kod")) or ESLEMELER.get((g or {}).get("esle"))',
        'return ESLEMELER.get((g or {}).get("esle"))', r"^A(1|3) .*bust"),
    "MR0 kontrol: yorum eklendi": ("def esle_bust(g, dizin, rh):\n", "def esle_bust(g, dizin, rh):  # kontrol\n", None),
}
MUTANT_MANIFEST = {
    "MR3 manifest logo renk_kosul silindi": ('        renk_kosul: { taban: [{ alan: "taban", degerler: ["Var"] }] },\n', "",
                                             r"^A2 (KOSUL-UYUMSUZ|GIZLI-KOSUL) logo\.taban"),
}


def mutant(ad):
    d = tempfile.mkdtemp(prefix="renk-esleme-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        kos, man = os.path.join(d, "tools", "foto-uretec-kosucu.py"), os.path.join(d, "foto-uretim-veri.js")
        ks, ms = open(KOSUCU, encoding="utf-8").read(), open(MANIFEST, encoding="utf-8").read()
        eski, yeni, kalip = MUTANT_KOSUCU.get(ad) or MUTANT_MANIFEST[ad]
        hedef = ks if ad in MUTANT_KOSUCU else ms
        if hedef.count(eski) != 1:
            return False, "capa %d kez" % hedef.count(eski)
        if ad in MUTANT_KOSUCU:
            ks = ks.replace(eski, yeni)
        else:
            ms = ms.replace(eski, yeni)
        open(kos, "w", encoding="utf-8").write(ks)
        open(man, "w", encoding="utf-8").write(ms)
        kirmizi, _ = kapi(kos, man)
        if kalip is None:
            return not kirmizi, "kirmizi=%d %s" % (len(kirmizi), "; ".join(kirmizi)[:200])
        return any(re.search(kalip, k) for k in kirmizi), "; ".join(kirmizi)[:200] or "KIRMIZI YOK"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    kirmizi, tablo = kapi(KOSUCU, MANIFEST)
    for kod in sorted(tablo):
        print("ESLEME %-10s %s" % (kod, "BAGLI" if tablo[kod] else "KOPUK"))
    for k in kirmizi:
        print("KIRMIZI " + k)
    bagli = sum(1 for v in tablo.values() if v)
    print("RENK_ESLEME %d/%d tur" % (bagli, len(tablo)))
    vaka = 1 if kirmizi or bagli != len(tablo) else 0
    survivor = 0
    print("MUTANTLAR")
    for ad in list(MUTANT_KOSUCU) + list(MUTANT_MANIFEST):
        ok, ek = mutant(ad)
        print("%s %s — %s" % ("✅" if ok else "❌", ad, ek))
        survivor += 0 if ok else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (vaka, survivor))
    return 0 if vaka == 0 and survivor == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
