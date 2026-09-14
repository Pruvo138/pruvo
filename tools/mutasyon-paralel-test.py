#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`mutasyon_kopya.paralel_sirali` KABUL TESTİ + MUTASYON KANITI.

🔴 NEDEN VAR (14 Eyl 2026): SERIT B mutasyon bataryaları paralele alındı
(`marka-bolum-mutasyon.py`). Paralel yardımcı SESSİZCE iki şeyi bozabilir ve ikisi de
bataryanın rc'sini değiştirmeden hükmü çürütür:
  · SONUÇ SIRASI bitiş sırasına kayarsa (`as_completed`) tablo satırları yanlış mutanta
    atfedilir / TABAN yerine bir mutantın kümesi taban sayılır;
  · İSTİSNA yutulursa çöken mutant "koştu" sayılır.
Bu yüzden sözleşmeler burada İDDİA olarak durur ve `--mutasyon` her bozuk varyantın en az
bir iddiayı kırmızı yaktığını, kontrol varyantının YEŞİL kaldığını ölçer.

Kullanım: python3 tools/mutasyon-paralel-test.py [--mutasyon]
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.realpath(__file__))
ENV = "MUTASYON_PARALEL_TEST"


def _yukle(yol):
    spec = importlib.util.spec_from_file_location("mk_paralel_olcum", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iddialar(mk):
    """Döner: [(ad, gecti, ayrinti), ...]."""
    sonuc = []
    os.environ.pop(ENV, None)

    # S1 SIRA: ilk iş EN GEÇ biter; sonuç yine girdi sırasında olmalı.
    def _uyu(i, sure):
        time.sleep(sure)
        return i
    isler = [(0, 0.6), (1, 0.4), (2, 0.2), (3, 0.0)]
    os.environ[ENV] = "4"
    donen = mk.paralel_sirali(isler, _uyu, ENV)
    sonuc.append(("S1_SIRA_GIRDI_SIRASI", donen == [0, 1, 2, 3], "donen=%r" % (donen,)))

    # S2 PARALELLİK: 4 × 0,5 sn iş 4 işçide < 1,5 sn (sıralı olsa 2 sn).
    bas = time.time()
    mk.paralel_sirali([(i, 0.5) for i in range(4)], _uyu, ENV)
    sure = time.time() - bas
    sonuc.append(("S2_GERCEKTEN_PARALEL", sure < 1.5, "sure=%.2f sn" % sure))

    # S3 İSTİSNA YUTULMAZ: çöken iş sonucu okuyana fırlar.
    def _cok(i):
        if i == 2:
            raise ValueError("mutant-cokme")
        return i
    try:
        mk.paralel_sirali([(i,) for i in range(4)], _cok, ENV)
        sonuc.append(("S3_ISTISNA_FIRLAR", False, "istisna yutuldu"))
    except ValueError as e:
        sonuc.append(("S3_ISTISNA_FIRLAR", "mutant-cokme" in str(e), "fırladı: %s" % e))

    # S4 GEÇERSİZ ENV FAIL-CLOSED: "0" / "iki" DURDURUR, sessizce varsayılana düşmez.
    for deger in ("0", "iki"):
        os.environ[ENV] = deger
        try:
            mk.paralel_isci_sayisi(ENV)
            sonuc.append(("S4_GECERSIZ_ENV_%s" % deger, False, "durmadı"))
        except SystemExit:
            sonuc.append(("S4_GECERSIZ_ENV_%s" % deger, True, "SystemExit"))

    # S5 VARSAYILAN = min(tavan, çekirdek)
    os.environ.pop(ENV, None)
    beklenen = max(1, min(4, os.cpu_count() or 1))
    olcum = mk.paralel_isci_sayisi(ENV)
    sonuc.append(("S5_VARSAYILAN", olcum == beklenen,
                  "olcum=%d beklenen=%d" % (olcum, beklenen)))
    return sonuc


# (ad, eski, yeni, beklenen kırmızı iddia önekleri)
MUTANTLAR = [
    ("P1_BITIS_SIRASI",
     "        return list(ex.map(lambda a: fn(*a), isler))",
     "        from concurrent.futures import as_completed\n"
     "        return [f.result() for f in as_completed([ex.submit(fn, *a) for a in isler])]",
     {"S1_SIRA_GIRDI_SIRASI"}),
    ("P2_ISTISNA_YUTULUR",
     "        return list(ex.map(lambda a: fn(*a), isler))",
     "        def _yut(a):\n"
     "            try:\n"
     "                return fn(*a)\n"
     "            except Exception:\n"
     "                return None\n"
     "        return list(ex.map(_yut, isler))",
     {"S3_ISTISNA_FIRLAR"}),
    ("P3_TEK_ISCI",
     "    with ThreadPoolExecutor(max_workers=paralel_isci_sayisi(env_adi, tavan)) as ex:",
     "    with ThreadPoolExecutor(max_workers=1) as ex:",
     {"S2_GERCEKTEN_PARALEL"}),
    ("P4_GECERSIZ_ENV_SESSIZ",
     "            raise SystemExit(\"HATA: %s pozitif tamsayı değil: %r\" % (env_adi, deger))",
     "            return max(1, min(tavan, os.cpu_count() or 1))",
     {"S4_GECERSIZ_ENV_0", "S4_GECERSIZ_ENV_iki"}),
]
KONTROL = ("K0_YORUM",
           "def paralel_sirali(isler, fn, env_adi, tavan=4):",
           "def paralel_sirali(isler, fn, env_adi, tavan=4):  # kontrol: yalnız yorum",
           set())


def _bas(sonuc):
    for ad, gecti, ayrinti in sonuc:
        print("  %s %-24s %s" % ("GECTI" if gecti else "KALDI", ad, ayrinti))


def mutasyon():
    canli = os.path.join(TOOLS, "mutasyon_kopya.py")
    with open(canli, "rb") as f:
        sha_once = f.read()
    hatalar = []
    tmp = tempfile.mkdtemp(prefix="mutasyon-paralel-mut-")
    try:
        with io.open(canli, encoding="utf-8") as f:
            govde = f.read()
        for ad, eski, yeni, beklenen in MUTANTLAR + [KONTROL]:
            if govde.count(eski) != 1:
                hatalar.append("%s CAPA %d eşleşme (1 olmalı)" % (ad, govde.count(eski)))
                print("  HATA %-24s CAPA BAYAT (%d)" % (ad, govde.count(eski)))
                continue
            yol = os.path.join(tmp, ad, "mutasyon_kopya.py")
            os.makedirs(os.path.dirname(yol))
            with io.open(yol, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni, 1))
            # Ayrı süreç: env/iş parçacığı durumu mutantlar arasında taşınmaz.
            p = subprocess.run([sys.executable, os.path.realpath(__file__), "--modul", yol],
                               capture_output=True, text=True, timeout=120)
            satirlar = (p.stdout or "").splitlines()
            kirmizi = {s.split()[1] for s in satirlar if s.strip().startswith("KALDI ")}
            if not any(s.strip().startswith(("GECTI ", "KALDI ")) for s in satirlar):
                hatalar.append("%s ÇÖKME rc=%d" % (ad, p.returncode))
                print("  HATA %-24s ÇÖKME rc=%d | %s" % (ad, p.returncode,
                      ((p.stderr or "").strip().splitlines() or [""])[-1][:150]))
                continue
            ok = kirmizi == beklenen
            if not ok:
                hatalar.append("%s beklenen %s, ölçülen %s" % (ad, sorted(beklenen), sorted(kirmizi)))
            print("  %-4s %-24s KIRMIZI=%s (beklenen %s)"
                  % ("OK" if ok else "HATA", ad, ",".join(sorted(kirmizi)) or "-",
                     ",".join(sorted(beklenen)) or "-"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(canli, "rb") as f:
        if f.read() != sha_once:
            hatalar.append("CANLI mutasyon_kopya.py DEĞİŞTİ")
    print("MUTASYON: %d mutant + 1 kontrol · beklentiyi tutmayan: %d %s"
          % (len(MUTANTLAR), len(hatalar), hatalar or ""))
    return 1 if hatalar else 0


def main():
    args = sys.argv[1:]
    if "--mutasyon" in args:
        return mutasyon()
    yol = args[args.index("--modul") + 1] if "--modul" in args \
        else os.path.join(TOOLS, "mutasyon_kopya.py")
    sonuc = iddialar(_yukle(yol))
    _bas(sonuc)
    kaldi = sum(1 for _a, g, _d in sonuc if not g)
    print("IDDIA=%d/%d" % (len(sonuc) - kaldi, len(sonuc)))
    return 1 if kaldi else 0


if __name__ == "__main__":
    sys.exit(main())
