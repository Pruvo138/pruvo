#!/usr/bin/env python3
"""KABUL: tools/kopru-grup-kos.py (kopru-15 grup kosucusu) — HERMETIK, CI'da kosar.

Sahte kayit (KOPRU_KAYIT) + sahte uretec deposu (FOTO_KOSUCU_JENERATOR) + sahte komut koşucusu
(KOPRU_GRUP_SAHTE: uretec/cwebp/wrangler/curl/olcum komutlarini taklit eder, her cagriyi gunluge yazar) +
izole TMPDIR. Ag YOK, wrangler YOK, calisma agacina YAZMAZ (mutantlar `exec` ile bellekte kosar).
VAKALAR
  V1 --kuru: tur basina 4 adim (render/r2/d1/olcum) + D1 = pruvo-katalog-onizleme -c onizleme toml, canli ad YOK
  V2 mutlu yol: RENDER=ok R2=200 D1=ok HAZIR=evet, adim sirasi render<r2<d1<olcum, KOPRU_GRUP 2/2 rc=0,
     gecici dizin kalmadi
  V3 anahtarlik uretec (isimlik_uret) rc 2 -> RENDER=uretec-rc2 + R2/D1 kosmaz + yapboz yine ok (DEVAM) + rc 1
     + gecici dizin kalmadi
  V4 HTTP 404 -> R2=404, D1 KOSMAZ (acilmaz), rc 1
  V5 D1 rc 1 -> D1=rc1:..., rc 1
  V6 yer tutucu: dosya (yapboz `gorsel`) -> gecerli PNG; anahtarlik -> anahtarlik kaydi + isimlik_uret.py
     (kayit URETEC adiyla bulunur, tur adi != uretec adi); kopru kaydi olmayan tur (bust, plaket) ->
     uretec-ya-da-kayit-yok (fail-closed)
EVREN (sayfa-3adim K3d): manifest foto-uretim-veri.js TEK KAYNAK; kopru kayitlari yapboz + anahtarlik.
  Silinen tur grup vakalari yapboz/anahtarlik'a cevrildi; ses'e bagli V7 (dizi yer tutucusu) + MG1 SILINDI
  (kalan kopru kaydinda `dizi` yer tutucusu yok, tasinamaz).
MUTANTLAR (KIRMIZI yakmali): MD1 D1 adi canliya · MD2 d1 komutu canli adla kurulur (koruma) ·
  MR2 R2 200 denetimi silindi · MTMP gecici dizin silme kaldirildi
Cikti son satiri: VAKA_KIRMIZI=<n> SURVIVOR=<n>   (rc 0 yalniz ikisi de 0)
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "kopru-grup-kos.py")

SAHTE = r'''
import json, os, sys
a = sys.argv[1:]
with open(os.environ["SAHTE_LOG"], "a") as f:
    f.write(json.dumps(a) + "\n")
hata = os.environ.get("SAHTE_HATA", "")
s = " ".join(a)
if "_uret.py" in s and "--cikti" in a:
    if hata and hata in s:
        sys.stderr.write("RET: sahte uretec reddi\n"); sys.exit(2)
    c = a[a.index("--cikti") + 1]
    os.makedirs(c, exist_ok=True)
    open(os.path.join(c, "onizleme.png"), "wb").write(b"\x89PNG sahte")
elif a and a[0].endswith("cwebp"):
    open(a[-1], "wb").write(b"RIFF sahte webp")
elif "r2" in a and "put" in a:
    if hata == "r2":
        sys.stderr.write("403 sahte\n"); sys.exit(1)
elif "d1" in a and "execute" in a:
    if hata == "d1":
        sys.stderr.write("d1 sahte hata\n"); sys.exit(1)
elif a and a[0] == "curl":
    sys.stdout.write(os.environ.get("SAHTE_HTTP", "200"))
elif "foto-ornek-uc-uca.py" in s:
    kod = a[a.index("--tur") + 1]
    print("TUR %s => HAZIR" % kod)
    for e in "①②③④⑤⑥":
        print("  %s HAZIR sahte" % e)
    print("HAZIR=1/1 rc=0")
'''

KAYIT = {"surum": 1, "kayitlar": [
    {"kod": "yapboz", "uretec": "yapboz_uret", "cikti": {"onizleme_png": "onizleme.png"},
     "parametreler": [{"ad": "gorsel", "tip": "dosya"}, {"ad": "uzun_kenar_mm", "tip": "sayi"},
                      {"ad": "renkler", "tip": "renk_liste"}],
     "ornek": {"girdi": {"gorsel": "<PNG YOLU> (gri gradyan, oran <= 4:1)", "uzun_kenar_mm": 150,
                         "renkler": ["#C8B89A"]}}},
    {"kod": "anahtarlik", "uretec": "isimlik_uret", "cikti": {"onizleme_png": "onizleme.png"},
     "parametreler": [{"ad": "satirlar", "tip": "metin", "liste": True}, {"ad": "genislik_mm", "tip": "sayi"}],
     "ornek": {"girdi": {"satirlar": ["Ayşe"], "genislik_mm": 45.0}}},
]}

sonuc = {}


def vaka(ad, gecti, ac=""):
    sonuc[ad] = bool(gecti)
    print(("✅ " if gecti else "❌ ") + ad + (" — " + ac if ac else ""))


class Ortam:
    def __init__(self):
        self.kok = tempfile.mkdtemp(prefix="kopru-grup-test-")
        self.tmp = os.path.join(self.kok, "tmp")
        self.jen = os.path.join(self.kok, "jen")
        os.makedirs(self.tmp)
        os.makedirs(self.jen)
        self.sahte = os.path.join(self.kok, "sahte.py")
        with open(self.sahte, "w") as f:
            f.write(SAHTE)
        self.kayit = os.path.join(self.kok, "kayit.json")
        with open(self.kayit, "w") as f:
            json.dump(KAYIT, f, ensure_ascii=False)
        self.log = os.path.join(self.kok, "log.jsonl")

    def kos(self, kaynak, argumanlar, **ek):
        open(self.log, "w").close()
        env = dict(os.environ, KOPRU_GRUP_SAHTE=self.sahte, KOPRU_KAYIT=self.kayit, FOTO_KOSUCU_JENERATOR=self.jen,
                   SAHTE_LOG=self.log, TMPDIR=self.tmp)
        env.pop("SAHTE_HATA", None)
        env.update(ek)
        kod = ("import sys;sys.argv=[%r]+%r;g={'__file__':%r,'__name__':'__main__'};"
               "exec(compile(%r,%r,'exec'),g)") % (ARAC, list(argumanlar), ARAC, kaynak, ARAC)
        p = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, env=env, timeout=300)
        with open(self.log) as f:
            cagrilar = [json.loads(s) for s in f if s.strip()]
        return p.returncode, p.stdout + p.stderr, cagrilar

    def artik(self):
        return [d for d in os.listdir(self.tmp) if d.startswith("kopru-grup-")]

    def sil(self):
        shutil.rmtree(self.kok, ignore_errors=True)


def satir(cikti, onek):
    return [s for s in cikti.splitlines() if s.startswith(onek)]


def vakalar(o, kaynak, sus=False):
    """Tum vakalari kosar; donus: {vaka: gecti}."""
    r = {}

    def yaz(ad, gecti, ac=""):
        r[ad] = bool(gecti)
        if not sus:
            vaka(ad, gecti, ac)
    turler = ["--tur", "yapboz", "--tur", "anahtarlik"]

    rc, out, _ = o.kos(kaynak, turler + ["--kuru"])
    k = satir(out, "KURU ")
    adimlar = {(s.split()[1], s.split()[2]) for s in k}
    d1 = [s for s in k if "ADIM=d1" in s]
    yaz("V1 kuru: tur basina 4 adim", rc == 0 and adimlar == {("tur=%s" % t, "ADIM=%s" % a) for t in ("yapboz", "anahtarlik")
                                                            for a in ("render", "r2", "d1", "olcum")}, "rc=%d" % rc)
    yaz("V1 kuru: D1 onizleme adi + toml, canli ad yok",
        len(d1) == 2 and all("d1 execute pruvo-katalog-onizleme --remote -c shop/wrangler.onizleme.toml" in s
                             and " pruvo-katalog " not in s for s in d1))

    rc, out, c = o.kos(kaynak, turler)
    ks = satir(out, "KOSU ")
    sira = [("render" if any("_uret.py" in x for x in a) else "r2" if "r2" in a else "d1" if "d1" in a
             else "olcum" if any("foto-ornek-uc-uca.py" in x for x in a) else None) for a in c]
    sira = [s for s in sira if s]
    yaz("V2 mutlu yol: tum adimlar ok",
        rc == 0 and len(ks) == 2 and all("RENDER=ok R2=200 D1=ok HAZIR=evet eksik=-" in s for s in ks)
        and satir(out, "KOPRU_GRUP")[-1:] == ["KOPRU_GRUP turler=2 hazir=2/2 rc=0"], "rc=%d %s" % (rc, ks))
    yaz("V2 adim sirasi SIRALI", sira == ["render", "r2", "d1", "olcum"] * 2, str(sira))
    d1c = [a for a in c if "d1" in a]
    yaz("V2 D1 cagrisi yalniz onizleme", len(d1c) == 2 and all(
        "pruvo-katalog-onizleme" in a and "pruvo-katalog" not in a for a in d1c))
    yaz("V2 gecici dizin silindi", o.artik() == [], str(o.artik()))

    rc, out, c = o.kos(kaynak, turler, SAHTE_HATA="isimlik_uret.py")
    ks = satir(out, "KOSU ")
    yaz("V3 uretec hatasi -> rc1 + adim adi + diger tur devam",
        rc == 1 and any(s.startswith("KOSU tur=anahtarlik RENDER=uretec-rc2:") and "R2=- D1=-" in s for s in ks)
        and any(s.startswith("KOSU tur=yapboz RENDER=ok R2=200 D1=ok") for s in ks)
        and satir(out, "KOPRU_GRUP")[-1:] == ["KOPRU_GRUP turler=2 hazir=2/2 rc=1"], str(ks))
    yaz("V3 hatada gecici dizin silindi", o.artik() == [], str(o.artik()))

    rc, out, c = o.kos(kaynak, ["--tur", "yapboz"], SAHTE_HTTP="404")
    ks = satir(out, "KOSU ")
    yaz("V4 HTTP 404 -> R2=404 + D1 acilmaz + rc1",
        rc == 1 and ks[:1] and "R2=404 D1=-" in ks[0] and not [a for a in c if "d1" in a], str(ks))

    rc, out, c = o.kos(kaynak, ["--tur", "yapboz"], SAHTE_HATA="d1")
    ks = satir(out, "KOSU ")
    yaz("V5 D1 hatasi -> D1=rc1 + rc1", rc == 1 and ks[:1] and "D1=rc1:" in ks[0], str(ks))

    return r


def yer_tutucu_vakasi(o):
    env = {"KOPRU_KAYIT": o.kayit, "FOTO_KOSUCU_JENERATOR": o.jen}
    os.environ.update(env)
    s = importlib.util.spec_from_file_location("kopru_grup_kos", ARAC)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    d = tempfile.mkdtemp(dir=o.tmp, prefix="yt-")
    u = m.ornek_girdisi(KAYIT["kayitlar"][0], d)
    png = open(u["gorsel"], "rb").read() if os.path.isfile(u.get("gorsel", "")) else b""
    vaka("V6 dosya yer tutucusu -> gecerli PNG", png.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in png[-12:])
    p = m.plan_kur(["anahtarlik"])[0]
    vaka("V6 anahtarlik -> anahtarlik kaydi + isimlik_uret.py", p.get("kayit", {}).get("kod") == "anahtarlik"
         and p.get("g", {}).get("betik", "").endswith("isimlik_uret.py"), str(p.get("hata")))
    ua = m.ornek_girdisi({"ornek": {"girdi": {"satirlar": ["A"]}}, "cagri": {"sabit": {"anahtarlik": True}}}, d)
    vaka("V6 anahtarlik ornek girdisi kopru cagri.sabit'i tasir (anahtarlik=true)", ua.get("anahtarlik") is True,
         str(sorted(ua)))
    yok = {q["kod"]: q.get("hata") for q in m.plan_kur(["bust", "plaket"])}
    vaka("V6 kopru kaydi olmayan tur (bust, plaket) -> uretec-ya-da-kayit-yok",
         yok == {"bust": "uretec-ya-da-kayit-yok", "plaket": "uretec-ya-da-kayit-yok"}, str(yok))
    shutil.rmtree(d, ignore_errors=True)


def pb_vakasi(o, kaynak):
    """FOTO KOLU (anahtarlik-foto, 9 Eki): GERCEK sabit kopru kaydiyla render komutu `cagri.parametre_bayraklari`
    (--konum, varsayilan sol-ust) + dosya girdisini (--girdi <plaket 3MF>) tasir; plan_kur kol kaydini ana turun
    `foto_kolu`ndan bulur. Donus (gecti, aciklama). `kaynak` = arac kaynagi (mutant MPB bunu bozar)."""
    d = tempfile.mkdtemp(dir=o.tmp, prefix="pb-")
    eski = os.environ.get("KOPRU_ORNEK_PLAKET")
    try:
        yol = os.path.join(d, "kgk.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak)
        plaket = os.path.join(d, "ornek.3mf")
        with open(plaket, "wb") as f:
            f.write(b"PK\x03\x04")
        os.environ["KOPRU_ORNEK_PLAKET"] = plaket
        sp = importlib.util.spec_from_file_location("kgk_pb_%d" % id(d), yol)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        with open(os.path.join(KOK, "jenerator", "kopru", "kopru_kayitlari.json"), encoding="utf-8") as f:
            kk = next(k for k in json.load(f)["kayitlar"] if k.get("kod") == "anahtarlik-foto")
        p = {"kod": "anahtarlik-foto", "g": {"betik": "jeneratorler/foto/plaket_kulak.py"}, "kayit": kk,
             "jen": "/JEN", "py": "PY"}
        with open(os.path.join(d, "girdi.json"), "w", encoding="utf-8") as f:
            json.dump(m.ornek_girdisi(kk, d), f)
        uretec = dict(m.render_komutlari(p, d)[0]).get("uretec")
        bek = ["PY", "/JEN/jeneratorler/foto/plaket_kulak.py", "--konum", "sol-ust", "--girdi", plaket,
               "--cikti", os.path.join(d, "cikti")]
        return uretec == bek, str(uretec)
    except Exception as e:  # cokerse KIRMIZI
        return False, "istisna %s: %s" % (type(e).__name__, e)
    finally:
        if eski is None:
            os.environ.pop("KOPRU_ORNEK_PLAKET", None)
        else:
            os.environ["KOPRU_ORNEK_PLAKET"] = eski
        shutil.rmtree(d, ignore_errors=True)


MUTANTLAR = [
    ("MD1 D1 adi canliya", 'D1_ONIZLEME = "pruvo-katalog-onizleme"', 'D1_ONIZLEME = "pruvo-katalog"'),
    ("MD2 d1 komutu canli adla", '"d1", "execute", D1_ONIZLEME', '"d1", "execute", D1_CANLI'),
    ("MR2 R2 200 denetimi silindi", 'return "200" if durum == "200" else durum', 'return "200"'),
    ("MTMP gecici dizin silme kaldirildi", "shutil.rmtree(dizin, ignore_errors=True)", "pass"),
]


def main():
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()
    o = Ortam()
    try:
        print("VAKALAR")
        vakalar(o, kaynak)
        yer_tutucu_vakasi(o)
        g, ac = pb_vakasi(o, kaynak)
        vaka("V7 anahtarlik-foto render komutu parametre_bayraklari (--konum sol-ust) + --girdi plaket 3MF", g, ac)
        vk = sum(1 for v in sonuc.values() if not v)
        print("MUTANTLAR")
        sv = 0
        for ad, eski, yeni in MUTANTLAR:
            if kaynak.count(eski) != 1:
                print("❌ %s — capa bulunamadi (SURVIVOR sayilir)" % ad)
                sv += 1
                continue
            r = vakalar(o, kaynak.replace(eski, yeni), sus=True)
            kirmizi = [k for k, v in r.items() if not v]
            if o.artik():
                for d in o.artik():
                    shutil.rmtree(os.path.join(o.tmp, d), ignore_errors=True)
            print(("✅ %s KIRMIZI (%s)" % (ad, ", ".join(kirmizi))) if kirmizi else "❌ %s SURVIVOR" % ad)
            sv += 0 if kirmizi else 1
        # MPB (foto kolu): parametre bayraklari okunmazsa (konum uretece gitmez) V7 KIRMIZI olmali.
        eski, yeni = "            uretec += [pb[ad], str(u[ad])]\n", "            pass\n"
        g = kaynak.count(eski) == 1 and not pb_vakasi(o, kaynak.replace(eski, yeni))[0]
        print(("✅ %s KIRMIZI (V7)" % "MPB parametre_bayraklari okunmaz") if g else "❌ MPB SURVIVOR")
        sv += 0 if g else 1
    finally:
        o.sil()
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (vk, sv))
    return 0 if vk == 0 and sv == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
