#!/usr/bin/env python3
"""GA4 MUTASYON SURUCUSU — IZOLASYON TESTI (SIGKILL sonrasi canli agac BIREBIR mi?).

🔴 NEDEN (7 Eki 2026): tools/ga4-olay-mutasyon.py mutanti CANLI dosyaya yaziyor, geri
almayi finally'ye birakiyordu. Surec SIGKILL / oturum olumuyle dusunce finally KOSMADI
ve canli `shop/src/olcum.js` icinde `purchase→satin_alma` mutant artigi kaldi. "finally
ile geri aliyorum" bir BEYANDIR; bu test onu OLUM ANINDA olcer.

YONTEM:
  (P) POZITIF — surucu alt surecte (kendi surec grubunda) baslar. "taban:" satiri
      gorundugu an taban suresi T olculur; ilk mutant kopya kurulumu + kapi kosusu da
      ~T surer, o yuzden surec T/2 sonra (ilk mutant kapinin ICINDEYKEN) surec grubuyla
      birlikte SIGKILL ile oldurulur. Sonra canli agactaki mutant hedeflerinin sha256'si
      oncekiyle BIREBIR olmali. Oldurme aninin pencereye dustugu da ayrica KANITLANIR:
      surucunun gecici dizinlerinden birinde (TMPDIR teste ait) hedeflerden biri canlidan
      FARKLI olmali (mutant uygulanmisti); kanit yoksa hukum OLCULEMEDI (rc=3).
  (M) MUTANT — surucunun EV'e yazan ESKI davranisi (yazma hedefi ROOT, kopya-ici bekcisi
      sonuk) izole bir sahte EV'de (`kopya_kok` + hedeflerin GERCEK kopyasi) ayni yontemle
      koşulur; sahte EV'deki hedef ozeti DEGISMIS olmali (test bu mutanti yakalamali).

Test canli agaca YAZMAZ ve canli agacta hicbir sey SILMEZ: butun gecici dizinler teste
ait tek bir mkdtemp kokunun altindadir ve yalniz o kok silinir.
CIKIS: 0 yesil · 1 kirmizi · 3 olculemedi.
KOSUM: python3 tools/ga4-olay-mutasyon-izole-test.py
"""
import hashlib
import importlib.util
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SURUCU_ADI = "ga4-olay-mutasyon.py"
TABAN_TAVAN_SN = 900

# Eski davranis (EV'e yazan surum): yazma hedefi kopya yerine ROOT olur ve yazma oncesi
# kopya-ici bekcisi soner. Capa 1'den farkli kez bulunursa mutant KURULAMAZ -> KIRMIZI.
ESKI_DAVRANIS = [
    ("yollar = {rel: gercek_dosya(kopya, rel) for rel, _, _ in duzen}",
     "yollar = {rel: os.path.join(ROOT, rel) for rel, _, _ in duzen}"),
    ("disarida = [rel for rel, y in yollar.items() if not kopyada_mi(y, kopya)]",
     "disarida = []"),
]

HATALAR = []
OLCULEMEDI = []


def kontrol(kosul, mesaj):
    print(("  ok  " if kosul else "  ❌  ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚠️  OLCULEMEDI: " + mesaj)
    OLCULEMEDI.append(mesaj)


def surucu_modulu():
    spec = importlib.util.spec_from_file_location("ga4_mutasyon_surucusu",
                                                  os.path.join(TOOLS, SURUCU_ADI))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ozet(yol):
    if not os.path.isfile(yol):
        return None
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ozetler(kok, hedefler):
    return {rel: ozet(os.path.join(kok, rel)) for rel in hedefler}


def kos_ve_oldur(surucu_yolu, cwd, tmpdir):
    """Surucuyu baslatir, taban suresinden turetilen anda surec grubunu SIGKILL ile oldurur.

    Donus: (taban_sn, bekleme_sn, hata). hata None degilse olcum yapilamadi."""
    ortam = dict(os.environ, TMPDIR=tmpdir, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.monotonic()
    p = subprocess.Popen([sys.executable, "-u", "-B", surucu_yolu], cwd=cwd, env=ortam,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    satirlar = queue.Queue()

    def oku():
        for s in p.stdout:
            satirlar.put(s)
        satirlar.put(None)

    threading.Thread(target=oku, daemon=True).start()
    taban, son = None, []
    try:
        while taban is None:
            kalan = TABAN_TAVAN_SN - (time.monotonic() - t0)
            if kalan <= 0:
                return None, None, "taban satiri %ds icinde gelmedi" % TABAN_TAVAN_SN
            try:
                s = satirlar.get(timeout=kalan)
            except queue.Empty:
                continue
            if s is None:
                return None, None, "surucu taban oncesi bitti: %s" % " | ".join(son[-4:])
            son.append(s.rstrip())
            if "taban: kapi YESIL" in s:
                taban = time.monotonic() - t0
        bekleme = taban / 2.0
        time.sleep(bekleme)
        if p.poll() is not None:
            return taban, bekleme, "surucu oldurme anindan ONCE bitti (rc=%s)" % p.returncode
        return taban, bekleme, None
    finally:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        p.wait()
        time.sleep(0.5)


def kopyada_mutant_kaniti(tmpdir, hedefler, canli):
    """Olen surucunun geride biraktigi kopyalarda canlidan FARKLI bir hedef var mi?"""
    for ad in sorted(os.listdir(tmpdir)):
        if not ad.startswith("ga4-mutant-"):
            continue
        repo = os.path.join(tmpdir, ad, "repo")
        for rel in hedefler:
            yol = os.path.join(repo, rel)
            if os.path.isfile(yol) and not os.path.islink(yol) and ozet(yol) != canli[rel]:
                return rel
    return None


def sahte_ev_kur(mod, kok, hedefler):
    """Izole sahte EV: `tools/` kopya, mutant hedefleri GERCEK kopya, gerisi bag."""
    sahte = mod.kopya_kok(kok)
    for rel in hedefler:
        mod.gercek_dosya(sahte, rel)
    for rel in hedefler:
        if not mod.kopyada_mi(os.path.join(sahte, rel), sahte):
            return None, "sahte EV hedefi kopya disinda: %s" % rel
    return sahte, None


def eski_davranisi_kur(sahte):
    yol = os.path.join(sahte, "tools", SURUCU_ADI)
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    for eski, yeni in ESKI_DAVRANIS:
        if govde.count(eski) != 1:
            return "mutant capasi %d kez bulundu (1 bekleniyordu): %s" % (govde.count(eski), eski)
        govde = govde.replace(eski, yeni, 1)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde)
    return None


def main():
    print("=" * 70)
    print("GA4 MUTASYON SURUCUSU — IZOLASYON TESTI (SIGKILL)")
    print("=" * 70)
    mod = surucu_modulu()
    hedefler = sorted({rel for m in mod.MUTANTLAR for rel, _, _ in mod.duzenlemeler(m)})
    print("  hedefler: %s" % ", ".join(hedefler))

    test_kok = tempfile.mkdtemp(prefix="ga4-izole-test-")
    if os.path.realpath(test_kok).startswith(os.path.realpath(ROOT) + os.sep):
        print("HATA: test koku canli agacin icinde: %s" % test_kok)
        return 3
    try:
        # (P) POZITIF — gercek surucu, gercek EV
        print("\n(P) gercek surucu canli EV'de; ilk mutant kapidayken SIGKILL")
        once = ozetler(ROOT, hedefler)
        tmp_p = os.path.join(test_kok, "p")
        os.mkdir(tmp_p)
        taban, bekleme, hata = kos_ve_oldur(os.path.join(TOOLS, SURUCU_ADI), ROOT, tmp_p)
        if hata:
            olculemedi("pozitif kosum: " + hata)
        else:
            print("      taban=%.1fs · SIGKILL @ taban+%.1fs" % (taban, bekleme))
            kanit = kopyada_mutant_kaniti(tmp_p, hedefler, once)
            if kanit is None:
                olculemedi("oldurme aninda kopyada uygulanmis mutant bulunamadi "
                           "(pencere tutmadi)")
            else:
                print("      kanit: olum aninda mutant kopyada uygulanmisti (%s)" % kanit)
            sonra = ozetler(ROOT, hedefler)
            degisen = [rel for rel in hedefler if sonra[rel] != once[rel]]
            kontrol(not degisen, "POZITIF: SIGKILL sonrasi canli %d hedef BIREBIR%s"
                    % (len(hedefler), "" if not degisen else " DEGIL — " + ", ".join(degisen)))

        # (M) MUTANT — EV'e yazan eski davranis, izole sahte EV'de
        print("\n(M) eski davranis (EV'e yazan surum) izole sahte EV'de; ayni SIGKILL")
        sahte, hata = sahte_ev_kur(mod, os.path.join(test_kok, "m"), hedefler)
        if not hata:
            hata = eski_davranisi_kur(sahte)
        if hata:
            kontrol(False, "MUTANT kurulamadi: " + hata)
        else:
            once_m = ozetler(sahte, hedefler)
            tmp_m = os.path.join(test_kok, "mt")
            os.mkdir(tmp_m)
            taban, bekleme, hata = kos_ve_oldur(os.path.join(sahte, "tools", SURUCU_ADI),
                                                sahte, tmp_m)
            if hata:
                olculemedi("mutant kosum: " + hata)
            else:
                print("      taban=%.1fs · SIGKILL @ taban+%.1fs" % (taban, bekleme))
                sonra_m = ozetler(sahte, hedefler)
                degisen = [rel for rel in hedefler if sonra_m[rel] != once_m[rel]]
                kontrol(bool(degisen), "MUTANT eski davranis -> KIRMIZI (sahte EV'de degisen: %s)"
                        % (", ".join(degisen) or "YOK — test eski davranisi GORMUYOR"))
    finally:
        shutil.rmtree(test_kok, ignore_errors=True)

    print("-" * 70)
    if HATALAR:
        print("SONUC: KIRMIZI ❌")
        for h in HATALAR:
            print("   · " + h)
        return 1
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️")
        for m in OLCULEMEDI:
            print("   · " + m)
        return 3
    print("SONUC: YESIL ✅ — surucu olum aninda canli agaca iz birakmiyor; "
          "eski (EV'e yazan) davranis KIRMIZI yakalaniyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
