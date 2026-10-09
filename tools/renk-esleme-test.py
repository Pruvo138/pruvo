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
import types

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
        if palet and kod == "bust":
            # A3 PALET (bust): 2 renk -> iki_renk true; 1 renk -> yalniz ilk bolge, iki_renk false. (Okan 9 Eki: formda
            # "iki_renk" alani YOK — kosul tur koduna bagli; eskiden form alanina bagliydi, alan kalkinca dal SESSIZCE
            # yapboz koluna duserdi.)
            if u.get("iki_renk") is not True:
                kirmizi.append("A3 PALET %s iki renk odendi, iki_renk=%r" % (kod, u.get("iki_renk")))
                ok = False
            u1, d1 = kos_esle(p_ac, {palet[0]: renk[palet[0]]})
            if u1.get("iki_renk") is not False or d1 != palet[:1]:
                kirmizi.append("A3 PALET %s tek renk: iki_renk=%r donus=%s" % (kod, u1.get("iki_renk"), d1))
                ok = False
        elif palet:
            # A3 PALET (yapboz, K3c): odenen N renk -> donus palet[:N] ve uretec listesi AYNI sirada N hex.
            for n in range(1, len(palet) + 1):
                rn = {b: renk[b] for b in palet[:n]}
                un, dn = kos_esle(p_ac, rn)
                liste = [h.upper() for h in un.get("renkler") or []]
                if dn != palet[:n] or liste != [rh[renk[b]].upper() for b in palet[:n]]:
                    kirmizi.append("A3 PALET %s %d renk: donus=%s renkler=%s" % (kod, n, dn, liste))
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


# K3a (8 Eki 2026): 15 tür silindi. Kalan 4: plaket/figur/yapboz/bust. Eski mutantlarin
# cogu silinen turlere (qr/logo/ses/isimlik) bagliydi -> capa noop olurdu. null/no-op mutant YASAK.
# MR1/MR5 bust icin; yalniz A3 PALET kapsamiyla daraltildi.
MUTANT_KOSUCU = {
    # A3 PALET: bust'ta `u["iki_renk"] = "rolyef" in secilen` silinirse iki_renk uyumsuz -> A3 PALET.
    "MR1 esle_bust iki_renk baglama silindi": ('    u["iki_renk"] = "rolyef" in secilen\n', "", r"^A3 PALET bust"),
    # ESLE secimi (tur onceligi) silinirse esle_bust yerine varsayilan (tekin_kos uretec) -> A3 PALET.
    "MR5 esle secimi uretece dondu (tur onceligi silindi)": (
        'return ESLEMELER.get((t or {}).get("kod")) or ESLEMELER.get((g or {}).get("esle"))',
        'return ESLEMELER.get((g or {}).get("esle"))', r"^A(1|3) .*bust"),
    # K3c A3 PALET (yapboz): odenen palet renkleri uretecin `renkler` listesine gitmezse -> A1 RENK-GITMEZ / A3 PALET.
    "MR6 esle_yapboz palet listesi uretece gecmiyor": (
        '    if renkler:\n        u["renkler"] = renkler\n', "", r"^A(1 RENK-GITMEZ|3 PALET) yapboz"),
    "MR0 kontrol: yorum eklendi": ("def esle_bust(g, dizin, rh):\n", "def esle_bust(g, dizin, rh):  # kontrol\n", None),
}
# MR2/MR3/MR4 silinen tur (qr/logo/ses) bagimliydi — capa artik kaynak dosyada yok; SİLİNDİ.
MUTANT_MANIFEST = {}


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


def bust_zinciri(kos):
    """V5 + V7 (Okan 9 Eki 20:2x): SIPARIS ZINCIRI — kalem (yeni form: iki_renk/uzun_kenar_mm YOK) -> siparis_girdisi ->
    uretim esle fonksiyonu. V5 Renkli (2 foto rengi) -> iki_renk true + taban/rolyef 2 hex; ana renk -> false + 1 renk;
    uzun_kenar_mm = olcu_mm (Olcu surgusu). V7 ters acik/kapali -> esle ciktisinda `ters` farkli. -> kirmizi listesi."""
    turler = {t.get("kod"): t for t in ESLE.node(MANIFEST) if isinstance(t, dict)}
    t, rh, kirmizi = turler.get("bust"), kos.renk_tablosu(), []
    if not t:
        return ["V5 bust kaydi yok"]
    adlar = []
    for ad, hx in rh.items():
        if hx.upper() not in [rh[a].upper() for a in adlar]:
            adlar.append(ad)
    d = tempfile.mkdtemp(prefix="renk-esleme-bust-")
    try:
        def zincir(renkler, ters):
            kalem = {"foto_is": "b" * 32, "foto_renkler": renkler, "foto_secim": {"govde_malzeme": "PLA"},
                     "parametreler": {"rolyef_yuksekligi_mm": 4, "ters": ters}}
            gi = kos.siparis_girdisi({"urunler": json.dumps([kalem]), "kalem": 0, "is_no": "b" * 32, "tur": "bust",
                                      "siparis_no": "V5", "olcu_mm": 120}, t)
            g = dict(gi, dosyalar=ESLE._dosyalar(d))
            u, don = kos.esle_fonksiyonu(t, kos.cli_tablosu().get(t.get("uretec")))(g, d, rh)
            return gi, u, don
        gi, u, don = zincir(adlar[:2], False)
        if not (u.get("iki_renk") is True and don == ["taban", "rolyef"] and
                str(u.get("renk_taban")).upper() == rh[adlar[0]].upper() and
                str(u.get("renk_rolyef")).upper() == rh[adlar[1]].upper() and "iki_renk" not in gi["parametreler"] and
                "renk_liste" not in u and "renkler" not in u):
            kirmizi.append("V5 RENKLI iki_renk=%r donus=%s taban=%s rolyef=%s" % (
                u.get("iki_renk"), don, u.get("renk_taban"), u.get("renk_rolyef")))
        if u.get("uzun_kenar_mm") != 120.0:
            kirmizi.append("V5 OLCU uzun_kenar_mm=%r (olcu_mm 120 beklenir)" % u.get("uzun_kenar_mm"))
        _, u1, d1 = zincir(adlar[:1], False)
        if not (u1.get("iki_renk") is False and d1 == ["taban"] and str(u1.get("renk_taban")).upper() == rh[adlar[0]].upper() and
                "renk_liste" not in u1 and "renkler" not in u1):
            kirmizi.append("V5 ANA RENK iki_renk=%r donus=%s" % (u1.get("iki_renk"), d1))
        _, ua, _ = zincir(adlar[:1], True)
        if not (ua.get("ters") is True and u1.get("ters") is False):
            kirmizi.append("V7 TERS acik=%r kapali=%r" % (ua.get("ters"), u1.get("ters")))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return kirmizi


def bellek_modulu(metin):
    """Mutant BELLEK kopyasi (diske yazma YOK): kosucu kaynagi degistirilip yeni modul nesnesine derlenir."""
    m = types.ModuleType("kosucu_bellek_mutant")
    m.__file__ = KOSUCU
    exec(compile(metin, KOSUCU, "exec"), m.__dict__)
    return m


def main():
    kirmizi, tablo = kapi(KOSUCU, MANIFEST)
    kirmizi += bust_zinciri(modul("kosucu_bust_zinciri", KOSUCU))
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
    # M3 (bellek): Renkli bustte iki_renk false gider -> V5 KIRMIZI.
    ks = open(KOSUCU, encoding="utf-8").read()
    capa = '    u["iki_renk"] = "rolyef" in secilen\n'
    if ks.count(capa) != 1:
        ok, ek = False, "capa %d kez" % ks.count(capa)
    else:
        mk = bust_zinciri(bellek_modulu(ks.replace(capa, '    u["iki_renk"] = False\n')))
        ok, ek = any(k.startswith("V5 RENKLI") for k in mk), "; ".join(mk)[:200] or "KIRMIZI YOK"
    print("%s %s — %s" % ("✅" if ok else "❌", "M3 Renkli bustte iki_renk false gider (bellek) -> V5", ek))
    survivor += 0 if ok else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (vaka, survivor))
    return 0 if vaka == 0 and survivor == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
