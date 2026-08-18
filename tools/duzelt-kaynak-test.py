#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/duzelt-kaynak-test.py — K171 kapsam: --kaynak-durum / --kaynak-temizle.

GERCEK .urun-kaynaklari.json'a DOKUNULMAZ: sahte repo (<tmp>/urunler.json +
<tmp>/.urun-kaynaklari.json) kurulur. duzelt.py yollari kendi __file__ konumundan
turettigi icin kopya sahte katalog uzerinde calisir.

Kabul eksenleri:
  K1  --kaynak-durum: dosya TAM ise `KAYNAK_KAYIT=N URUN=N ARTIK=N ARTIK_ORNEK=ids`
                     (sadece id, govde YOK), rc=0.
  K2  --kaynak-durum: dosya YOK ise OLCULEMEDI + rc != 0.
  K3  --kaynak-temizle yalniz kullanilirsa hata (rc=2).
  K4  --kaynak-temizle + --sil: ayni flock icinde KAYNAKLAR da dusurulur.
  K5  --kaynak-temizle + --sil: idempotent (ZATEN_YOK raporlanir, hata degil).
  K6  --kaynak-temizle + --toplu: batch'teki urun_silmeler KAYNAKLAR'dan dusurulur.
  K7  --kaynak-temizle: temizlik ONCESI/SONRASI iki olcum KAYNAK_KAYIT ve KALAN
      uzerinden tutarli (gercek yazim, "yazma kaldirildi" mutantini yakalar).
  K8  --kaynak-temizle: dosyaya KAYIT GOVDESI BASILMAZ (sadece id + sayi).
      Bu eksen asagidaki kisisel-veri-test'i davet eder; burada 'uyelik'/'link'
      gecmedigini GORUNEN cikti uzerinden teyit ederiz.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
DUZELT = os.path.join(TOOLS, "duzelt.py")
YARDIMCILAR = ("gorsel_koken.py", "arama.py")

FAILS = []


def kontrol(kosul, mesaj, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))


def cagir(repo, *argv):
    """Gerçek duzelt.py'yi sahte repoda çalıştır; (rc, stdout, stderr) döndür."""
    yeni = {
        "PYTHONPATH": os.path.join(repo, "tools"),
    }
    env = os.environ.copy()
    env.update(yeni)
    r = subprocess.run(
        [sys.executable, os.path.join(repo, "tools", "duzelt.py")] + list(argv),
        capture_output=True, text=True, env=env,
    )
    return r.returncode, r.stdout, r.stderr


def sahte_repo(kaynaklar=None, urunler=None):
    """Sahte repo: <tmp>/urunler.json + <tmp>/.urun-kaynaklari.json + tools/duzelt.py."""
    d = tempfile.mkdtemp(prefix="duzelt-kaynak-testi-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy2(DUZELT, os.path.join(d, "tools", "duzelt.py"))
    for y in YARDIMCILAR:
        shutil.copy2(os.path.join(TOOLS, y), os.path.join(d, "tools", y))
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(
            urunler if urunler is not None
            else [{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                   "aciklama": "a", "fiyat": "100 TL",
                   "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
            f, ensure_ascii=False, indent=2)
    if kaynaklar is not None:
        with open(os.path.join(d, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
            json.dump(kaynaklar, f, ensure_ascii=False, indent=2)
    return d


def temizle(*dizinler):
    for d in dizinler:
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("K171 — --kaynak-durum / --kaynak-temizle kabul testi (sahte repo)\n")

    # ── K1: --kaynak-durum, TAM dosya ────────────────────────────────────────
    print("K1 — --kaynak-durum (TAM dosya)")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x", "uyelik": "u1"},
                   "u-yok": {"link": "https://y", "uyelik": "u2"},
                   "u-yok2": {"link": "https://z", "uyelik": "u3"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_KAYIT=3" in out, "KAYNAK_KAYIT=3", "out=%r" % out.strip())
        kontrol("URUN=1" in out, "URUN=1", "out=%r" % out.strip())
        kontrol("ARTIK=2" in out, "ARTIK=2", "out=%r" % out.strip())
        kontrol("u-yok" in out and "u-yok2" in out, "ARTIK_ORNEK 2 id'yi icerir")
        # K8: kayit govdesi (link/uyelik) BASILMAMALI
        kontrol("https://x" not in out and "https://y" not in out and "https://z" not in out,
                "Ciktida LINK yok", "out=%r" % out)
        kontrol("\"uyelik\"" not in out and "u1" not in out and "u2" not in out and "u3" not in out,
                "Ciktida UYELIK degeri yok", "out=%r" % out)
    finally:
        temizle(repo)

    # ── K2: --kaynak-durum, dosya YOK ───────────────────────────────────────
    print("\nK2 — --kaynak-durum (dosya YOK)")
    repo = sahte_repo(kaynaklar=None)  # dosya yok
    try:
        rc, out, err = cagir(repo, "--kaynak-durum")
        kontrol(rc != 0, "rc != 0 (sessiz sifir YASAK)", "rc=%d" % rc)
        kontrol("OLCULEMEDI" in err, "stderr OLCULEMEDI icerir", "err=%r" % err.strip())
    finally:
        temizle(repo)

    # ── K3: --kaynak-temizle yalniz ──────────────────────────────────────────
    print("\nK3 — --kaynak-temizle yalniz (ARGUMAN HATASI)")
    repo = sahte_repo()
    try:
        rc, out, err = cagir(repo, "--kaynak-temizle")
        kontrol(rc == 2, "rc=2", "rc=%d" % rc)
        kontrol("kaynak-temizle" in err, "hata mesaji kaynak-temizle iceriyor")
    finally:
        temizle(repo)

    # ── K4: --kaynak-temizle + --sil (tek urun) ─────────────────────────────
    print("\nK4 — --kaynak-temizle + --sil (tek urun)")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x"}, "u-diger": {"link": "https://w"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=1" in out, "KAYNAK_SILINEN=1", "out=%r" % out)
        kontrol("ZATEN_YOK=0" in out, "ZATEN_YOK=0")
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1")
        # Dogrula: KAYNAKLAR dosyasi gercekten silinmis
        with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
            kalan = json.load(f)
        kontrol("u-var" not in kalan and "u-diger" in kalan,
                "KAYNAKLAR: u-var dustu, u-diger duruyor", "kalan=%s" % sorted(kalan))
    finally:
        temizle(repo)

    # ── K5: --kaynak-temizle + --sil IDEMPOTENT (id yoksa) ──────────────────
    print("\nK5 — --kaynak-temizle + --sil (idempotent: id YOK)")
    repo = sahte_repo(
        kaynaklar={"u-diger": {"link": "https://w"}},  # u-var kaynakta yok
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=0" in out, "KAYNAK_SILINEN=0", "out=%r" % out)
        kontrol("ZATEN_YOK=1" in out, "ZATEN_YOK=1")
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1")
    finally:
        temizle(repo)

    # ── K6: --kaynak-temizle + --toplu (batch) ──────────────────────────────
    print("\nK6 — --kaynak-temizle + --toplu (batch silme)")
    repo = sahte_repo(
        kaynaklar={"u-1": {"link": "https://1"}, "u-2": {"link": "https://2"},
                   "u-3": {"link": "https://3"}},
        urunler=[
            {"id": "u-1", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-1-1.jpg"]},
            {"id": "u-2", "kategori": "Otomobil", "marka": ["X"], "baslik": "U2",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-2-2.jpg"]},
            {"id": "u-3", "kategori": "Otomobil", "marka": ["X"], "baslik": "U3",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-3-3.jpg"]},
        ],
    )
    try:
        islem = os.path.join(repo, "islem.json")
        with open(islem, "w", encoding="utf-8") as f:
            json.dump([
                {"id": "u-1", "sil": "test"},
                {"id": "u-2", "alan": "fiyat", "deger": "200 TL"},  # Duzeltme, silme degil
                {"id": "u-3", "sil": "test"},
            ], f, ensure_ascii=False)
        rc, out, err = cagir(repo, "--toplu", islem, "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=2" in out, "KAYNAK_SILINEN=2 (silinen 2)", "out=%r" % out)
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1 (u-2 kalici)", "out=%r" % out)
        with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
            kalan = json.load(f)
        kontrol(list(kalan.keys()) == ["u-2"], "yalniz u-2 kaldi", "kalan=%s" % sorted(kalan))
    finally:
        temizle(repo)

    # ── K7: --kaynak-temizle IKI OLcum (oncesi/sonrasi) ─────────────────────
    print("\nK7 — --kaynak-turum: ONCESI / SONRASI olcum tutarliligi")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x"}, "u-yok1": {"link": "1"},
                   "u-yok2": {"link": "2"}, "u-yok3": {"link": "3"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, _ = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0 and "ARTIK=3" in out, "ONCESI ARTIK=3", "out=%r" % out)

        # u-var'i sil --kaynak-temizle ile
        rc, out, _ = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "temizlik rc=0")
        kontrol("KAYNAK_SILINEN=1" in out, "KAYNAK_SILINEN=1", "out=%r" % out)

        rc, out, _ = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0 and "ARTIK=3" in out, "SONRASI ARTIK=3 (u-var zaten urunlerdeydi; "
                 "orphan'lar ayni kaldi)", "out=%r" % out)
    finally:
        temizle(repo)

    # ── K8: --kaynak-temizle ciktida govde YOK ───────────────────────────────
    print("\nK8 — --kaynak-temizle ciktisinda KAYIT GOVDESI yok")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://oops", "uyelik": "ucretsiz-uyelik-adi",
                              "lisans": "CC BY-NC"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("https://oops" not in out and "https://oops" not in err,
                "Ciktida/adimda LINK yok", "out=%r err=%r" % (out, err))
        kontrol("ucretsiz-uyelik-adi" not in out and "ucretsiz-uyelik-adi" not in err,
                "Ciktida UYELIK degeri yok", "out=%r err=%r" % (out, err))
        kontrol("CC BY-NC" not in out and "CC BY-NC" not in err,
                "Ciktida LISANS degeri yok", "out=%r err=%r" % (out, err))
    finally:
        temizle(repo)

    print("\n" + ("-" * 78))
    if FAILS:
        print("HATALI: %d iddia kirmizi" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        return 1
    print("HEPSI GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
