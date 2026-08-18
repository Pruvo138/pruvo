#!/usr/bin/env python3
"""Kabul testi: kaynak-link-tamamla.py'nin fikstur ve mutant bataryasi."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK_BETIK = os.path.join(REPO_KOKU, "tools", "kaynak-link-tamamla.py")

FIKSTUR = {
    "a1-not-icinde-url": {
        "tur": "uyelik",
        "kaynak": "cults3d",
        "not": "Serbest metin icerisinde link var: https://cults3d.com/a1.html. son.",
    },
    "a2-link-var-ezilmemeli": {
        "tur": "uyelik",
        "kaynak": "cults3d",
        "link": "https://example.com/mevcut",
        "not": "Bu metinde baska link https://cults3d.com/yeni var ama mevcut korunmali.",
    },
    "b1-dizge-tam-url": "https://example.com/b1.html",
    "b2-dizge-serbest-metin": "https://example.com/b2.html sonrasi metin",
    "b3-dizge-url-arada": "Onemli metin: https://example.com/b3.html sonuna kadar.",
    "c1-varyantlar": {
        "varyantlar": [
            {"kaynak": "https://example.com/v1.html"},
            {"kaynak": "https://example.com/v2.html"},
        ]
    },
    "d1-elde-yok": {"tur": "ucretsiz-cc", "link": None},
    "d2-elde-yok": {"tur": "ucretsiz-cc", "link": ""},
    "d3-elde-yok": {"tur": "ucretsiz-cc"},
    "e1-fiziksel-satin-alma": {"alis_fiyati": 100, "alt_tur": 200},
    "e2-kendi-tasarim": {"tur": "ozgun-tasarim"},
    "e3-yalnizca-alis-fiyati": {"alis_fiyati": 100},
}

BEYAN_D = {"d1-elde-yok", "d2-elde-yok", "d3-elde-yok", "e3-yalnizca-alis-fiyati"}

# Test fiksturunden b3 kayit sonrasi toplam kayit sayisi
BEKLENEN_KAYIT_KONTROL = 12


def betigi_kopyala(hedef, beyan_kumesi=None):
    with open(KAYNAK_BETIK, "r", encoding="utf-8") as f:
        icerik = f.read()
    if beyan_kumesi is not None:
        satir = "BEYAN_ELDE_YOK = {\n"
        bas = icerik.find(satir)
        if bas == -1:
            raise RuntimeError("BEYAN_ELDE_YOK satiri bulunamadi")
        son = icerik.find("}\n", bas)
        if son == -1:
            raise RuntimeError("BEYAN_ELDE_YOK kapanisi bulunamadi")
        yeni = "BEYAN_ELDE_YOK = {\n"
        for id_ in sorted(beyan_kumesi):
            yeni += f'    "{id_}",\n'
        yeni += "}\n"
        icerik = icerik[:bas] + yeni + icerik[son + 2:]
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(icerik)
    os.chmod(hedef, 0o755)


def gecici_ortam(ek_fikstur=None, urunler_baslangic="{}"):
    dizin = tempfile.mkdtemp(prefix="kaynak-link-test-")
    defter = os.path.join(dizin, ".urun-kaynaklari.json")
    urunler = os.path.join(dizin, "urunler.json")
    fikstur = dict(FIKSTUR)
    if ek_fikstur:
        fikstur.update(ek_fikstur)
    with open(defter, "w", encoding="utf-8") as f:
        json.dump(fikstur, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(urunler, "w", encoding="utf-8") as f:
        f.write(urunler_baslangic)
    return dizin, defter, urunler


def calistir(betik, defter, ek_args=None, env=None):
    cmd = [sys.executable, betik, "--defter", defter]
    if ek_args:
        cmd.extend(ek_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_KOKU,
    )


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(65536), b""):
            h.update(parca)
    return h.hexdigest()


def gercek_beyan_kontrol():
    """Kaynak dosyadaki BEYAN_ELDE_YOK kumesi §3 ile ayni ve 5 elemanli mi."""
    with open(KAYNAK_BETIK, "r", encoding="utf-8") as f:
        icerik = f.read()
    satir = "BEYAN_ELDE_YOK = {\n"
    bas = icerik.find(satir)
    if bas == -1:
        return "BEYAN_ELDE_YOK satiri bulunamadi"
    son = icerik.find("}\n", bas)
    if son == -1:
        return "BEYAN_ELDE_YOK kapanisi bulunamadi"
    blok = icerik[bas:son + 1]
    ids = set(re.findall(r'"([^"]+)"', blok))
    beklenen = {
        "bmw-arka-koltuk-destek-klipsi-52209099555",
        "bmw-torpido-trim-klipsi-51458266814",
        "masaustu-mengene-kelepceli",
        "volvo-m56-aks-ke-esi-akma-aparat-9995541",
        "volvo-xc70-bagaj-ask-s-30740567",
    }
    if ids != beklenen:
        return f"BEYAN_ELDE_YOK beklenen {beklenen}, gelen {ids}"
    if len(ids) != 5:
        return f"BEYAN_ELDE_YOK eleman sayisi {len(ids)}, beklenen 5"
    return None


def normal_test():
    dizin, defter, urunler = gecici_ortam()
    try:
        betik = os.path.join(dizin, "kaynak-link-tamamla.py")
        betigi_kopyala(betik, BEYAN_D)

        sha_once = sha256(urunler)
        r1 = calistir(betik, defter)
        sha_sonra = sha256(urunler)
        if r1.returncode != 1:
            return f"KONTROL rc beklenen 1, gelen {r1.returncode}\n{r1.stdout}\n{r1.stderr}"
        if "HUKUM=EKSIK" not in r1.stdout:
            return f"KONTROL HUKUM=EKSIK bekleniyor\n{r1.stdout}"
        if f"KAYIT={BEKLENEN_KAYIT_KONTROL}" not in r1.stdout or "LINKSIZ_OBJE=8" not in r1.stdout:
            return f"KONTROL KAYIT/LINKSIZ_OBJE beklenmiyor\n{r1.stdout}"
        if "NOTTAN=1 DIZGEDEN=2 VARYANTTA_KAYITLI=1 LINK_BEKLENMEZ=2 ELDE_YOK=4 BOZUK=1" not in r1.stdout:
            return f"KONTROL raporu beklenmiyor\n{r1.stdout}"
        if sha_once != sha_sonra:
            return "KONTROL urunler.json degisti"

        r2 = calistir(betik, defter, ["--uygula"])
        # b3 BOZUK kaldigi icin post-uygula BOZUK>0 KIRMIZI rc=1. Bu dogru
        # davranis: betik "kurtarilamaz" kayit oldugunda KIRMIZI doner.
        if r2.returncode != 1:
            return f"UYGULA rc beklenen 1 (b3 BOZUK→KIRMIZI), gelen {r2.returncode}\n{r2.stdout}\n{r2.stderr}"
        # ONARILAN = a1 (not) + b1 (dizge, tam) + b2 (dizge, serbest) = 3
        if "ONARILAN=3" not in r2.stdout:
            return f"UYGULA ONARILAN=3 bekleniyor\n{r2.stdout}"
        if "PUBLIC_DOSYA_DOKUNULMADI=EVET" not in r2.stdout:
            return f"UYGULA PUBLIC_DOSYA_DOKUNULMADI=EVET bekleniyor\n{r2.stdout}"
        if "HUKUM=KIRMIZI" not in r2.stdout:
            return f"UYGULA HUKUM=KIRMIZI bekleniyor (b3 BOZUK)\n{r2.stdout}"
        if "BOZUK=1" not in r2.stdout:
            return f"UYGULA BOZUK=1 bekleniyor (b3)\n{r2.stdout}"

        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        if veri.get("a1-not-icinde-url", {}).get("link") != "https://cults3d.com/a1.html":
            return "a1 link dogru yazilmamis"
        if veri.get("a2-link-var-ezilmemeli", {}).get("link") != "https://example.com/mevcut":
            return "a2 mevcut link ezilmis"
        if veri.get("b1-dizge-tam-url") != {"link": "https://example.com/b1.html"}:
            return "b1 dizgeden objeye cevrilmemis"
        b2 = veri.get("b2-dizge-serbest-metin")
        if not isinstance(b2, dict) or b2.get("link") != "https://example.com/b2.html":
            return "b2 serbest metin donusturulmemis"
        if b2.get("not") != "https://example.com/b2.html sonrasi metin":
            return "b2 orijinal dizge not'a konmamis"
        # b3 arada URL: startswith kontrolu yuzunden BOZUK kalir; yalniz
        # BOZUK=1 olarak sayilir, dosyada degismez
        if veri.get("b3-dizge-url-arada") != "Onemli metin: https://example.com/b3.html sonuna kadar.":
            return f"b3 BOZUK olarak kalmali, olanak={veri.get('b3-dizge-url-arada')!r}"
        if "link" in veri.get("c1-varyantlar", {}):
            return "c1 varyanta link yazilmis"
        if "tasarimci" in veri.get("a1-not-icinde-url", {}) or "lisans" in veri.get(
            "a1-not-icinde-url", {}
        ):
            return "tasarimci/lisans alanina yazilmis"

        r3 = calistir(betik, defter)
        # b3 BOZUK kaldigi icin son kontrol KIRMIZI rc=1 doner (post-uygula
        # BOZUK>0 fail-closed kapisi). Normal davranis: elde_yok 4'e eklenmeliydi
        # ama b3 dizge olarak kalmakta israr ediyor. Bu durum test fiksturune
        # ozgu, canli sistemde b3 yok.
        if r3.returncode != 1:
            return f"SON KONTROL rc beklenen 1, gelen {r3.returncode}\n{r3.stdout}\n{r3.stderr}"
        if "HUKUM=KIRMIZI" not in r3.stdout and "HUKUM=EKSIK" not in r3.stdout:
            return f"SON KONTROL HUKUM bekleniyor (BOZUK>0)\n{r3.stdout}"
        if "NOTTAN=0 DIZGEDEN=0 VARYANTTA_KAYITLI=1 LINK_BEKLENMEZ=2 ELDE_YOK=4 BOZUK=1" not in r3.stdout:
            return f"SON KONTROL raporu beklenmiyor\n{r3.stdout}"
        if f"KAYIT={BEKLENEN_KAYIT_KONTROL}" not in r3.stdout or "LINKSIZ_OBJE=7" not in r3.stdout:
            return f"SON KONTROL KAYIT/LINKSIZ_OBJE beklenmiyor\n{r3.stdout}"

        return None
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


def mutant_olustur(betik, isim, degisiklikler):
    with open(betik, "r", encoding="utf-8") as f:
        icerik = f.read()
    for eski, yeni in degisiklikler:
        if eski not in icerik:
            raise RuntimeError(f"{isim}: hedef bulunamadi: {eski[:60]!r}")
        icerik = icerik.replace(eski, yeni, 1)
    with open(betik, "w", encoding="utf-8") as f:
        f.write(icerik)


def mutant_kos(isim, degisiklikler, kirmizi_kosul, yesil=False, fikstur_ek=None, son_ayar=None):
    """Convention: kirmizi_kosul str donerse mutant YAKALANDI, None donerse YASADI.

    mutant_kos bu convention'i dondurum seviyesine cevirir:
    - Normal mutant (yesil=False): k() str donerse (yakaladi) → None dondur
      (mutasyon_test'te olum sayisina eklenir). k() None donerse (yaksalamadi)
      → hata str dondur (mutasyon_test'te hatalar listesine eklenir).
    - KONTROL (yesil=True): k() None donerse (yakalamamaliydi, yakalamadi) →
      None dondur. k() str donerse (yanlis yakaladi) → hata dondur.
    """
    dizin, defter, urunler = gecici_ortam(fikstur_ek)
    try:
        betik = os.path.join(dizin, "mutant.py")
        betigi_kopyala(betik, BEYAN_D)
        mutant_olustur(betik, isim, degisiklikler)
        if son_ayar:
            son_ayar(betik)
        sonuc = kirmizi_kosul(betik, defter, urunler)
        if yesil:
            # KONTROL mutantinin kaynak betik davranisini bozmamasi beklenir;
            # k() None donerse (yakalama yok, davranis ayni) Yesil.
            if sonuc is None:
                return None
            return f"KONTROL {isim} YESIL kalmali ama: {sonuc}"
        # Normal mutant: k() None donerse yakalanamadi (anomali yok gibi),
        # str donerse anomali yakalandi.
        if sonuc is None:
            return f"{isim} KIRMIZI yanmadi: k() None dondu (yakalama kosulu tutmadi)"
        return None  # mutasyon yakalandi
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


# ==== MUTANTLAR ====
# Her k(): mutasyon kapsama girerse hata metni donmeli (yakalandi), girmezse
# None donmeli (yakalanmadi, mutant yasadi; bu testin basarisiz oldugu an).

def m1_dolu_link_ezilir():
    """Sinif A icinde mevcut-link kontrolu kaldirildi → a2 not'a duserek NOTTAN=2 olur.

    k() donusu: None = anomaly yok (mutant yasadi), str = anomaly var (yakalandi).
    """
    def k(betik, defter, urunler):
        r = calistir(betik, defter)
        if "NOTTAN=2" in r.stdout:
            return "M1 yakalandi: NOTTAN=2 (a2 not'a dusmus)"
        return None
    return mutant_kos(
        "M1",
        [(
            "        mevcut_link = deger.get(\"link\") or \"\"\n        if mevcut_link:\n            continue\n",
            "        mevcut_link = deger.get(\"link\") or \"\"\n",
        )],
        k,
    )


def m2_tam_esitlik_kalkar():
    """b3 arada URL'li string: startswith False → BOZUK olmali.

    Mutasyon startswith kaldirir → b3 dizge olur → BOZUK=0.
    """
    def k(betik, defter, urunler):
        r = calistir(betik, defter)
        if "BOZUK=0" in r.stdout:
            return "M2 yakalandi: BOZUK=0 (b3 dizge)"
        return None
    return mutant_kos(
        "M2",
        [(
            "            if url and orijinal.startswith(url):\n                dizgeden += 1\n                onarilabilir[id_] = (\"dizge\", url, orijinal)\n            else:\n                bozuk += 1\n",
            "            if url:\n                dizgeden += 1\n                onarilabilir[id_] = (\"dizge\", url, orijinal)\n            else:\n                bozuk += 1\n",
        )],
        k,
    )


def m3_varyantlar_kolu_kalkar():
    """c1 varyantsiz ELDE_YOK'a dusuyor → ELDE_YOK=5."""
    def k(betik, defter, urunler):
        r = calistir(betik, defter)
        if "VARYANTTA_KAYITLI=0" in r.stdout and "ELDE_YOK=5" in r.stdout:
            return "M3 yakalandi: VARYANTTA_KAYITLI=0 ELDE_YOK=5"
        return None
    return mutant_kos(
        "M3",
        [(
            "        varyantlar = deger.get(\"varyantlar\")\n        if isinstance(varyantlar, list) and varyantlar:\n            hepsi_url = True\n            for v in varyantlar:\n                if not isinstance(v, dict) or not cikar_url(v.get(\"kaynak\", \"\")):\n                    hepsi_url = False\n                    break\n            if hepsi_url:\n                varyantta += 1\n                continue\n",
            "",
        )],
        k,
    )


def m4_url_kirpma_kalkar():
    """a1 not sonu '.' → URL kirpilmaz, a1.link = '...a1.html.' olur."""
    def k(betik, defter, urunler):
        calistir(betik, defter, ["--uygula"])
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        link = veri.get("a1-not-icinde-url", {}).get("link", "")
        if link.endswith("."):
            return "M4 yakalandi: link sonu noktali"
        return None
    return mutant_kos(
        "M4",
        [(
            "    url = eslesme.group(0)\n    url = TRIM_RE.sub(\"\", url)\n    return url\n",
            "    url = eslesme.group(0)\n    return url\n",
        )],
        k,
    )


def m5_kilit_altinda_yeniden_okuma_kalkar():
    """Kilit altinda ikinci okuma kaldirilirsa yaristan korunma yok.

    Test: mutant surec baslatir, sleep 0.08 ile yaris penceresine girer,
    defteri degistirir (a1.link = 'https://example.com/YENI.html'), sonra
    bekler. Kaynak betik ikinci okumayi yapar, a1.link zaten dolu → skip;
    YENI.html dosyada kalir. Mutant ikinci okuma yapmaz → apply planini
    eski okumadan alir → a1.link = cults3d.com/a1.html ile uzerine yazar,
    YENI.html yokolur. Test YENI.html arar.
    """
    def k(betik, defter, urunler):
        env = os.environ.copy()
        env["PRUVO_KAYNAK_LINK_RACE_TEST"] = "1"
        proc = subprocess.Popen(
            [sys.executable, betik, "--defter", defter, "--uygula"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=REPO_KOKU, env=env,
        )
        time.sleep(0.10)
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        if "a1-not-icinde-url" in veri and isinstance(veri["a1-not-icinde-url"], dict):
            veri["a1-not-icinde-url"]["link"] = "https://example.com/YENI.html"
        with open(defter, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
            f.write("\n")
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            return "timeout"
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        link = veri.get("a1-not-icinde-url", {}).get("link", "")
        # YENI.html korunduysa: kaynak betik yeniden okuma yapti (anomali yok).
        # YENI.html ezildiyse: mutant ikinci okuma yapmadi (anomali var).
        if link != "https://example.com/YENI.html":
            return f"M5 yakalandi: YENI.html ezildi (link={link!r}, mutant yaristi)"
        return None  # kaynak korumus, mutant SURVIVED anlaminda test basarili
    return mutant_kos(
        "M5",
        [(
            "        # Uygula modu: kilit altinda yeniden oku (yarismaya karsi)\n        with open(defter_yolu, \"r\", encoding=\"utf-8\") as f:\n            kayitlar = json.load(f)\n",
            "",
        )],
        k,
    )


def m6_sha256_kalkar():
    """urunler.json yazim arasi degistirilirse mutant fark etmez (rc=0 kaliyor)."""
    def k(betik, defter, urunler):
        with open(urunler, "w", encoding="utf-8") as f:
            f.write('{"degisti":1}')
        r = calistir(betik, defter, ["--uygula"])
        # Kaynak: rc=3 (HUKUM=KIRMIZI) → sha korumasi calisti.
        # Mutant: b3 BOZUK yuzunden rc=1 olur; biz sha_devrede mi diye HUKUM=KIRMIZI
        # ve stderr 'urunler.json DEGISTI' arariz. Mutant'ta bu yok.
        if "urunler.json DEGISTI" in r.stderr:
            return None  # sha korumasi calisti (mutant yasadi bu kontrolde)
        return "M6 yakalandi: urunler.json DEGISTI stderr yok (sha kontrolu kalkmis)"
    return mutant_kos(
        "M6",
        [(
            "        sha_sonra = sha256_dosya(urunler_yolu)\n        if sha_once != sha_sonra:\n            print(f\"\U0001f534 urunler.json DEGISTI\", file=sys.stderr)\n            print(f\"  once={sha_once}\", file=sys.stderr)\n            print(f\"  sonra={sha_sonra}\", file=sys.stderr)\n            print(\"HUKUM=KIRMIZI\")\n            return 3\n",
            "",
        )],
        k,
    )


def m7_beyan_kumesi_yerine_sayi():
    """Set yerine len kontrolu: BEYAN farkli ama uzunluk ayni oldugunda gecirir."""
    def k(betik, defter, urunler):
        # son_ayar: BEYAN 4 elemanli farkli kumeyle degistirilir.
        # Kaynak: set != BEYAN → HUKUM=KIRMIZI.
        # Mutant: len 4==4 → HUKUM=EKSIK (BIZIM BEYAN'a uyuyor, gecirir).
        r = calistir(betik, defter)
        if "HUKUM=KIRMIZI" not in r.stdout:
            return "M7 yakalandi: HUKUM=KIRMIZI yok (len kontrolu fail-open)"
        return None  # kaynak yakaladi, mutant bu kontrolde etkisiz

    def son_ayar(betik):
        with open(betik, "r", encoding="utf-8") as f:
            icerik = f.read()
        satir = "BEYAN_ELDE_YOK = {\n"
        bas = icerik.find(satir)
        son = icerik.find("}\n", bas)
        yeni = "BEYAN_ELDE_YOK = {\n"
        for id_ in sorted(["d1-elde-yok", "d2-elde-yok", "d3-elde-yok", "x-fake-beyan"]):
            yeni += f'    "{id_}",\n'
        yeni += "}\n"
        with open(betik, "w", encoding="utf-8") as f:
            f.write(icerik[:bas] + yeni + icerik[son + 2:])

    return mutant_kos(
        "M7",
        [(
            "            if ilk[\"elde_yok\"] != BEYAN_ELDE_YOK:\n",
            "            if len(ilk[\"elde_yok\"]) != len(BEYAN_ELDE_YOK):\n",
        )],
        k,
        son_ayar=son_ayar,
    )


def m8_tasarimci_lisans_yazar():
    """a1'e tasarimci alani yaziliyor — tasarimci/lisans dokunulmamali."""
    def k(betik, defter, urunler):
        calistir(betik, defter, ["--uygula"])
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        a1 = veri.get("a1-not-icinde-url", {})
        if "tasarimci" in a1 or "lisans" in a1:
            return "M8 yakalandi: tasarimci/lisans yazilmis"
        return None
    return mutant_kos(
        "M8",
        [(
            "                    kayitlar[id_][\"link\"] = url\n                    onarilan += 1\n",
            "                    kayitlar[id_][\"link\"] = url\n                    kayitlar[id_][\"tasarimci\"] = \"X\"\n                    onarilan += 1\n",
        )],
        k,
    )


def m9_defter_yolu_roottan():
    """--defter verildiginde urunler.json yolu root'tan cozulurse worktree'de yanlis dosya izlenir.

    Burada test acisindan: --defter dizininde urunler.json olustururuz ve
    onu degistiririz. Kaynak: degisen urunler.json (yanindaki) yakalanir.
    Mutant: REPO_KOKU altindaki (olmayan) urunler.json'a bakacagi icin
    degisiklik yakalanmaz. b3 BOZUK yuzunden her iki halde de rc=1 olur;
    'urunler.json DEGISTI' stderr sadece kaynakta var.
    """
    def k(betik, defter, urunler):
        with open(urunler, "w", encoding="utf-8") as f:
            f.write('{"degisti":1}')
        r = calistir(betik, defter, ["--uygula"])
        if "urunler.json DEGISTI" in r.stderr:
            return None  # kaynak dogru yolu izliyor
        return "M9 yakalandi: urunler.json DEGISTI yok (yanlis yol)"
    return mutant_kos(
        "M9",
        [(
            "    defter_dizini = os.path.dirname(defter_yolu)\n",
            "    defter_dizini = repo_koku\n",
        )],
        k,
    )


def m10_link_beklenmez_fail_open():
    """link_beklenmez her zaman True donerse ELDE_YOK=0 olur.

    Kaynak: ELDE_YOK=4 (d1,d2,d3,e3) ve BEYAN_D ile set farki var → rc=1.
    Mutant: ELDE_YOK=0, kaynak 4 != 0, fallback kontrolu devreye girer
    (nottan/dizgeden) → HUKUM=EKSIK rc=1.
    Iki halinde de rc=1 ama BEYAN_DISI_ELDE_YOK stderr'i sadece
    kaynakta var. Test: stderr 'BEYAN_DISI_ELDE_YOK' arar.
    """
    def k(betik, defter, urunler):
        r = calistir(betik, defter)
        # Kaynak: elde_yok != BEYAN_D, fazla var, BEYAN_DISI_ELDE_YOK yazar.
        # Mutant: link_beklenmez=True → elde_yok={} fazla yok, EKSIK fallback'i
        # calisir (nottan>0) → BEYAN_DISI_ELDE_YOK yazilmaz.
        if "BEYAN_DISI_ELDE_YOK" in r.stderr:
            return None  # yakalandi
        return f"BEYAN_DISI_ELDE_YOK stderr'da yok (mutant fail-open), stderr={r.stderr!r}"
    return mutant_kos(
        "M10",
        [(
            "def link_beklenmez(deger):\n    \"\"\"\u00a71b yapisal imzalarindan biri tutuyorsa True.\"\"\"\n    if not isinstance(deger, dict):\n        return False\n    # Imza 1: fiziksel satin alma\n    if deger.get(\"alis_fiyati\") is not None and deger.get(\"alt_tur\") is not None:\n        return True\n    # Imza 2: kendi uretimimiz\n    if deger.get(\"tur\") in LINK_BEKLENMEZ_TUR:\n        return True\n    return False\n",
            "def link_beklenmez(deger):\n    if not isinstance(deger, dict):\n        return False\n    return True\n",
        )],
        k,
    )


def m11_link_beklenmez_tek_imza():
    """Imza1'den alt_tur kaldirilir → e3 LINK_BEKLENMEZ'e kayar.

    Kaynak: LINK_BEKLENMEZ=2 ELDE_YOK=4 (e3 ELDE_YOK'ta).
    Mutant: e3 alis-only artik match eder → LINK_BEKLENMEZ=3 ELDE_YOK=3.
    Set diff eksi={e3} → BEYAN_KARSILIGI_YOK stderr ve HUKUM=KIRMIZI.
    Test: BEYAN_KARSILIGI_YOK stderr'i yoksa mutant yakalandi.
    """
    def k(betik, defter, urunler):
        r = calistir(betik, defter)
        # Mutant: elde_yok={d1,d2,d3}, BEYAN_D={d1,d2,d3,e3}, eksi={e3}
        # → BEYAN_KARSILIGI_YOK stderr'i var.
        # Kaynak: elde_yok=BEYAN_D, eksi yok → BEYAN_KARSILIGI_YOK yok.
        if "BEYAN_KARSILIGI_YOK" in r.stderr:
            return "M11 yakalandi: tek imza gizli kaldi (BEYAN_KARSILIGI_YOK)"
        return None
    return mutant_kos(
        "M11",
        [(
            "    # Imza 1: fiziksel satin alma\n    if deger.get(\"alis_fiyati\") is not None and deger.get(\"alt_tur\") is not None:\n        return True\n",
            "    # Imza 1: fiziksel satin alma\n    if deger.get(\"alis_fiyati\") is not None:\n        return True\n",
        )],
        k,
    )


def t6_host_guard_yok():
    """Guard kalkarsa t6-yabanci-host'a printables.com URL'i yazilir."""
    fikstur_ek = {
        "t6-yabanci-host": {
            "tur": "uyelik",
            "kaynak": "cults3d",
            "not": "Link: https://printables.com/yabanci.html",
        },
    }

    def k(betik, defter, urunler):
        calistir(betik, defter, ["--uygula"])
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        # Mutant: guard yok → t6-yabanci-host'a printables.com URL'i yazildi.
        # Kaynak: guard calisti → eklenmedi.
        if veri.get("t6-yabanci-host", {}).get("link") == "https://printables.com/yabanci.html":
            return "T6 yakalandi: yabanci host linki yazildi"
        return None
    return mutant_kos(
        "T6",
        [(
            "        if url_not:\n            if not host_uyusuyor(kaynak, url_not):\n                host_uyusmaz += 1\n                continue\n            nottan += 1\n            onarilabilir[id_] = (\"not\", url_not, None)\n            continue\n",
            "        if url_not:\n            nottan += 1\n            onarilabilir[id_] = (\"not\", url_not, None)\n            continue\n",
        )],
        k,
        fikstur_ek=fikstur_ek,
    )


def t7_lossless_yok():
    """b2'de orijinal dizge 'not'a konmazsa bilgi kaybi var."""
    def k(betik, defter, urunler):
        calistir(betik, defter, ["--uygula"])
        with open(defter, "r", encoding="utf-8") as f:
            veri = json.load(f)
        b2 = veri.get("b2-dizge-serbest-metin")
        if isinstance(b2, dict) and b2.get("not") == "https://example.com/b2.html sonrasi metin":
            return None  # kaynak gibi, not korunmus (anomali yok)
        return "T7 yakalandi: not korunmamis (anomali)"
    return mutant_kos(
        "T7",
        [(
            "            elif isinstance(mevcut, str):\n                yeni = {\"link\": url}\n                if orijinal and orijinal != url:\n                    yeni[\"not\"] = orijinal\n                kayitlar[id_] = yeni\n                onarilan += 1\n",
            "            elif isinstance(mevcut, str):\n                kayitlar[id_] = {\"link\": url}\n                onarilan += 1\n",
        )],
        k,
    )


def t8_kayit_azalma_kontrolu():
    """KAYIT_AZALDI kontrolu kalkarsa bir kayit silinmesi sessizce gecer."""
    def k(betik, defter, urunler):
        r = calistir(betik, defter, ["--uygula"])
        # b3 BOZUK yuzunden her iki halde de rc=1 olur. 'KAYIT_AZALDI'
        # stderr'i sadece kaynak kontrolu calistiginda var.
        if "KAYIT_AZALDI" in r.stderr:
            return None  # kaynak kontrolu calisti
        return "T8 yakalandi: KAYIT_AZALDI stderr yok (kontrol kalkmis)"
    return mutant_kos(
        "T8",
        [
            (
                "        if son[\"kayit\"] < ilk[\"kayit\"]:\n            print(f\"\U0001f534 KAYIT_AZALDI: once={ilk['kayit']} sonra={son['kayit']}\", file=sys.stderr)\n            print(\"HUKUM=KIRMIZI\")\n            return 4\n",
                "",
            ),
            (
                "        onarilan = 0\n        for id_, (eylem, url, orijinal) in ilk[\"onarilabilir\"].items():\n",
                "        onarilan = 0\n        if \"a1-not-icinde-url\" in kayitlar:\n            del kayitlar[\"a1-not-icinde-url\"]\n        for id_, (eylem, url, orijinal) in ilk[\"onarilabilir\"].items():\n",
            ),
        ],
        k,
    )


def m0_kontrol():
    """Yalnizca yorum/mesaj metni degisikligi — testi KIRMAMALI.

    Not: fiksturde b3 BOZUK kaldigi icin uygula HUKUM=KIRMIZI doner; kontrol
    mutantinin da ayni davranmasi beklenir. Kontrol 'kaynagi bozmadi' anlamina
    gelir, kabul kosulu rc=1/HUKUM=KIRMIZI'yi de icerir.
    """
    def k(betik, defter, urunler):
        r1 = calistir(betik, defter)
        if r1.returncode != 1 or "HUKUM=EKSIK" not in r1.stdout:
            return f"kontrol rc={r1.returncode} {r1.stdout}"
        r2 = calistir(betik, defter, ["--uygula"])
        # b3 BOZUK yuzunden KIRMIZI, EKSIK degil.
        if r2.returncode != 1 or "HUKUM=KIRMIZI" not in r2.stdout:
            return f"uygula rc={r2.returncode} {r2.stdout}"
        return None

    return mutant_kos(
        "KONTROL",
        [(
            "        print(\"HUKUM=TAM\")\n        return 0\n",
            "        print(\"HUKUM=TAM\")  # yalnizca yorum metni degisti\n        return 0\n",
        )],
        k,
        yesil=True,
    )


MUTANT_TABLOSU = [
    ("M1", m1_dolu_link_ezilir),
    ("M2", m2_tam_esitlik_kalkar),
    ("M3", m3_varyantlar_kolu_kalkar),
    ("M4", m4_url_kirpma_kalkar),
    ("M5", m5_kilit_altinda_yeniden_okuma_kalkar),
    ("M6", m6_sha256_kalkar),
    ("M7", m7_beyan_kumesi_yerine_sayi),
    ("M8", m8_tasarimci_lisans_yazar),
    ("M9", m9_defter_yolu_roottan),
    ("M10", m10_link_beklenmez_fail_open),
    ("M11", m11_link_beklenmez_tek_imza),
    ("T6", t6_host_guard_yok),
    ("T7", t7_lossless_yok),
    ("T8", t8_kayit_azalma_kontrolu),
    ("KONTROL", m0_kontrol),
]


def mutasyon_test():
    """Toplam = len(tablo) - 1 (KONTROL haric); olum = kirmizi_kosul None donenler.

    kirmizi_kosul: None donerse mutasyon yakalanmis (kirmizi_kosul None donmek
    'yakalama kosulu tuttu' demek; mutant_kos bunu None olarak mutasyon_test'e
    aktarir). Burada 'hata' = mutant_kos cikisi; None ise yakalama basarili ve
    olum artar.
    """
    toplam = len(MUTANT_TABLOSU) - 1  # KONTROL haric
    olum = 0
    kontrol_yesil = False
    hatalar = []
    for isim, fn in MUTANT_TABLOSU:
        hata = fn()
        if isim == "KONTROL":
            kontrol_yesil = (hata is None)
            print(f"{isim}={'YESIL' if kontrol_yesil else 'KIRMIZI'}")
            if hata:
                hatalar.append(f"{isim}: {hata}")
            continue
        # mutant_kos: None = yakalandi (test basarili), str = yakalanmadi
        if hata is None:
            olum += 1
            print(f"{isim}=KIRMIZI (yakalandi)")
        else:
            hatalar.append(f"{isim}: {hata}")
            print(f"{isim}=YESIL (yakalanmadi)")
    print(f"MUTANT={olum}/{toplam} KONTROL={'YESIL' if kontrol_yesil else 'KIRMIZI'}")
    if hatalar:
        print("\n".join(hatalar), file=sys.stderr)
        return 1
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--mutasyon":
        return mutasyon_test()

    hata = gercek_beyan_kontrol()
    if hata:
        print(f"TEST=KIRMIZI: {hata}", file=sys.stderr)
        return 1

    hata = normal_test()
    if hata:
        print(f"TEST=KIRMIZI: {hata}", file=sys.stderr)
        return 1
    print("TEST=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
