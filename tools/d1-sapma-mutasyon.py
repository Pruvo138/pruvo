#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SINYAL AYRIMI (yayin sagligi ↔ D1 sapmasi) CURUTME (mutasyon) araci — 4 Agu 2026.

NE OLCER: "kabul testi YESIL" demek "eksen CANLI" demek DEGILDIR. Bu arac kol ayriminin
her eksenini BILEREK bozar ve `tools/cron-nabiz-kapisi.py --kendini-test`in GERCEKTEN
kirmizi yandigini SAYIYLA olcer.

NEDEN VAR (olculen kusur)
=========================
`d1-uzlastirici.yml`in sapma gorunurlugu adimi sapma bulunca BILEREK `exit 1` verir.
4 Agu'da bu is akisi `workflow_call` ile deploy.yml'in BLOKLAMAYAN `d1-kadans` koluna
baglandi. `d1-kadans` `deploy: needs`'te olmadigi icin yayini DURDURMUYOR — ama cagiran
kosumun GENEL `conclusion`'ini `failure` yapiyordu: TEK kirmizi IKI soruyu birden
cevapliyordu ("yayin calisti mi" + "D1 sapmasi var mi"). Bu depoda olculmus sinif:
[[hukum-yanlis-birimde]] — toplu sonuc tekil ekseni gizler.

🔴 EN KOLAY VE EN YANLIS COZUM: sapmayi SESSIZLESTIRMEK. Bu turun asil isi o cozumu
   KIRMIZI YAKMAKTIR — sinyali kaldiran, damgayi dusuren, alarm kanalini olduren ve iki
   HALI (onarildi / onarilamadi) tek kutuya yigan mutantlar burada TEK TEK olculur.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]): her mutant kosumunda IDDIA SAYISI taban
   kosumla AYNI olmali. Sayi dusuyorsa mutant testi COKERTMISTIR ve o kirmizi bir OLCUM
   DEGILDIR (cokme kirmiziyla karisir).

🔴 KONTROL MUTANTI SART ([[fikstur-degeri-mutasyon-koru]]): anlam tasimayan bir degisiklik
   (yorum metni, adim ADI) bataryayi kirmizi yakmamali — yoksa "oldu" hukumlerinin
   hicbiri mutasyona atfedilemez. ADIM ADI kontrolu ayrica bir IDDIADIR: siniflandirma
   ADA DEGIL ICRA EDILEN SEYE bakmalidir (ad bir mensiyondur, olcum degil).

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda kaynak sha256 karsilastirilir.

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/d1-sapma-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + kontrol mutantlari YESIL + iddia sayilari
korundu + canli kaynaklar sha256 olarak DEGISMEDI.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

KAPI = "tools/cron-nabiz-kapisi.py"
DEPLOY = os.path.join(".github", "workflows", "deploy.yml")
UZLASTIRICI = os.path.join(".github", "workflows", "d1-uzlastirici.yml")
ALARM = os.path.join(".github", "workflows", "d1-sapma-alarmi.yml")
HEDEFLER = (KAPI, DEPLOY, UZLASTIRICI, ALARM)
DOKUNULMAZ = [os.path.join(ROOT, y) for y in HEDEFLER]

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# DAYANAK METINLER (tek yerde — harness bayatlarsa GURULTULU duser)
# ─────────────────────────────────────────────────────────────────────────────
CRON_ADIM_BASI = ('      - name: "Sapma gorunurlugu (cron/elle kolu): '
                  'sapma olduysa kosum KIRMIZI"\n'
                  "        if: steps.olcum.outputs.sapma == 'var' "
                  "&& inputs.kadans_kolu != true\n")
DAMGA_ADIM_BASI = ('      - name: "Sapma damgasi (kadans kolu): '
                   'sapma AYRI kanaldan KIRMIZI yakar"\n'
                   "        if: steps.olcum.outputs.sapma == 'var' "
                   "&& inputs.kadans_kolu == true\n")
YUKLE_ADIMI = ('      - name: "Sapma damgasini yukle '
               '(artifact — d1-sapma-alarmi.yml bunu OKUR)"\n'
               "        if: steps.olcum.outputs.sapma == 'var' "
               "&& inputs.kadans_kolu == true\n"
               "        uses: actions/upload-artifact@v4\n"
               "        with:\n"
               "          name: d1-sapma-damgasi\n"
               "          path: d1-sapma-damgasi.json\n"
               "          if-no-files-found: error\n")
ONARILAMADI_KOSUL = "        if: failure() && steps.olcum.outputs.sapma == 'var'\n"
DAMGA_YAZ_SATIRI = ("          python3 tools/cron-nabiz-kapisi.py --damga-yaz "
                    "d1-sapma-damgasi.json --damga-adi d1-sapma-damgasi\n")

# ─────────────────────────────────────────────────────────────────────────────
# MUTANTLAR — (kod, aciklama, HEDEF, [(bulunacak, yerine), ...], kirmizi_mi)
# ─────────────────────────────────────────────────────────────────────────────

# ── (a) SAPMA SINYALINI SESSIZLESTIREN MUTANTLAR ────────────────────────────
S1 = ("S1", "🔴 SESSIZLESTIRME (kadans kolu): sapma damgasi yazma + yukleme adimlari "
            "SILINDI -> kadans kolunda sapma HICBIR YERDE kirmizi yakmaz; deploy "
            "conclusion'i 'temiz' gorunur cunku sinyal YOK EDILMISTIR", UZLASTIRICI,
      [(DAMGA_ADIM_BASI, "      - name: (silindi — mutant)\n        if: false\n"),
       (YUKLE_ADIMI, "")], True)

S2 = ("S2", "🔴 SESSIZLESTIRME (cron/elle kolu): sapma gorunurlugu adiminin KOSULU "
            "daima-yanlis yapildi -> cron kosumunda da sapma kirmizi yakmaz", UZLASTIRICI,
      [(CRON_ADIM_BASI, '      - name: "Sapma gorunurlugu (cron/elle kolu): '
                        'sapma olduysa kosum KIRMIZI"\n'
                        "        if: steps.olcum.outputs.sapma == 'yok-diye-bir-sey' "
                        "&& inputs.kadans_kolu != true\n")], True)

S11 = ("S11", "🔴 TERS SIZINTI: kadans kolunun damga adimina `exit 1` geri sizdi -> "
              "ONARILAN sapma cagiran YAYIN kosumunu yine kirmiziya cevirir (ayrim "
              "COZULMEZ, iki soru tek cikis koduna geri yigilir)", UZLASTIRICI,
       [(DAMGA_YAZ_SATIRI, DAMGA_YAZ_SATIRI + "          exit 1\n")], True)

# ── (c) CRON KOLUNUN `exit 1`'INI DUSUREN MUTANT ────────────────────────────
S3 = ("S3", "🔴 CRON KOLUNDAKI `exit 1` KALDIRILDI: kosumun TEK isi bu denetimken "
            "sapma artik hicbir cikis kodu uretmez (zamanlanmis kol SESSIZ)", UZLASTIRICI,
      [('          echo "Sapmanin KENDISI bir ust-yol kacagidir (pre-push kancasi / '
        'CI D1 adimi / elle push)." >> "$GITHUB_STEP_SUMMARY"\n'
        "          exit 1\n"
        "\n"
        "      # (2) KADANS KOLU",
        '          echo "Sapmanin KENDISI bir ust-yol kacagidir (pre-push kancasi / '
        'CI D1 adimi / elle push)." >> "$GITHUB_STEP_SUMMARY"\n'
        "\n"
        "      # (2) KADANS KOLU")], True)

# ── (d) "ONARILDI" ILE "ONARILAMADI"YI TEK HALE YIGAN MUTANTLAR ─────────────
S4 = ("S4", "🔴 IKI HAL TEK KUTUDA: `onarilamadi` adiminin `failure()` sarti dusuruldu -> "
            "hal 'sapma olustu' ile ayni kosula iner; kapanmayan sapma (Ege katalogun bir "
            "kismini goremez) ile onarilan sapma AYIRT EDILEMEZ", UZLASTIRICI,
      [(ONARILAMADI_KOSUL,
        "        if: steps.olcum.outputs.sapma == 'var'\n")], True)

S5 = ("S5", "🔴 ONARILAMADI HUKMU SILINDI: `failure()` kollu ayri adim kaldirildi -> "
            "emniyet agi tutmadiginda ortada ADIYLA konmus bir hukum kalmaz", UZLASTIRICI,
      [(ONARILAMADI_KOSUL, "        if: false\n")], True)

# ── (b) KADANS KOLUNU YAYIN YOLUNA SIZDIRAN MUTANT ─────────────────────────
S6 = ("S6", "🔴 KADANS KOLU YAYIN YOLUNA SIZDIRILDI: `d1-kadans` `deploy: needs` "
            "listesine eklendi -> D1/ag'a bagimli bir kol TUM EKIBIN yayinini durdurur "
            "VE iki kirmizi yine TEK birimde toplanir", DEPLOY,
      [("    needs: [build, serit-a2, serit-a3]\n",
        "    needs: [build, serit-a2, serit-a3, d1-kadans]\n")], True)

# ── KOL BAYRAGINI DUSUREN / TERSE CEVIREN MUTANTLAR ────────────────────────
S7 = ("S7", "🔴 KOL BAYRAGI DUSURULDU: `with: kadans_kolu: true` silindi -> cagrilan is "
            "varsayilan `false` ile kosar, ONARILAN sapmada `exit 1` verir ve deploy.yml "
            "conclusion'i YINE iki soruyu birden cevaplar", DEPLOY,
      [("    uses: ./.github/workflows/d1-uzlastirici.yml\n"
        "    with:\n      kadans_kolu: true\n",
        "    uses: ./.github/workflows/d1-uzlastirici.yml\n")], True)

S8 = ("S8", "🔴 VARSAYILAN TERSE CEVRILDI: `default: false` -> `true`. O zaman CRON kolu "
            "da kadans gibi davranir ve sapmada kirmizi yakmaz; sapma IKI KOLDAN DA "
            "susar (sessizlestirmenin en sinsi bicimi)", UZLASTIRICI,
      [("        type: boolean\n        required: false\n        default: false\n",
        "        type: boolean\n        required: false\n        default: true\n")], True)

# ── SAPMA ALARM KANALINI OLDUREN MUTANTLAR ─────────────────────────────────
S9 = ("S9", "🔴 ALARM KANALI OLDURULDU: d1-sapma-alarmi.yml'in GERCEK olcum adimi silindi "
            "(yalniz `--kendini-test` kaldi) -> alarm hicbir canli sey olcmez ama YESIL "
            "yanar; damga dogar, kimse okumaz", ALARM,
      [('      - name: "Olcum — tetikleyen yayin kosumunda D1 sapmasi oldu mu '
        '(ALARM; yayini DURDURMAZ)"\n'
        "        env:\n"
        "          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n"
        "          TETIK_KOSUM: ${{ github.event.workflow_run.id }}\n"
        "        run: python3 tools/d1-sapma-kapisi.py --gh-ozet\n", "")], True)

S10 = ("S10", "🔴 ALARM KANALI YAYIN YOLUNA BAGLANDI: d1-sapma-alarmi.yml'e `workflow_call` "
              "eklendi -> deploy.yml onu `uses:` ile cagirabilir ve sapma kirmizisi YINE "
              "deploy kosumunun conclusion'ina yigilir (ayrim COZULMEZ)", ALARM,
       [("  workflow_dispatch:\n", "  workflow_dispatch:\n  workflow_call:\n")], True)

S12 = ("S12", "🔴 ALARM `actions: read` YETKISI DUSURULDU: tetikleyen kosumun artifact "
              "listesi okunamaz -> alarm HER kosumda 'olculemedi' verir (olu kanal)", ALARM,
       [("  contents: read\n  actions: read", "  contents: read")], True)

# ── KONTROL MUTANTLARI (YESIL kalmali) ─────────────────────────────────────
K1 = ("K1", "ilgisiz: d1-uzlastirici.yml'de gorunurluk blogunun YORUM metni degistirildi "
            "(is akisi semantigi DEGISMEZ)", UZLASTIRICI,
      [("      # (1) CRON / ELLE KOLU — DAVRANIS 4 AGU ONCESIYLE BIREBIR AYNI.\n",
        "      # (1) CRON / ELLE KOLU — zamanlanmis ve elle kosumlar (yorum guncellendi).\n")],
      False)

K2 = ("K2", "ilgisiz: ADIM ADI degistirildi. Bu ayni zamanda bir IDDIADIR — siniflandirma "
            "ADA DEGIL ICRA EDILEN SEYE bakmali (ad bir mensiyondur, olcum degil)",
      UZLASTIRICI,
      [('      - name: "ONARILAMADI: sapma KAPANMADI (ayri hukum — her iki kolda KIRMIZI)"\n',
        '      - name: "Sapma kapanmadi (baska bir ad)"\n')], False)

K3 = ("K3", "ilgisiz: d1-sapma-alarmi.yml'e aciklama yorumu eklendi", ALARM,
      [("jobs:\n  sapma:\n", "jobs:\n  # sapma kanali — gerekce ustteki blokta\n  sapma:\n")],
      False)

MUTANTLAR = (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, K1, K2, K3)

IDDIA_RE = re.compile(r"^(\d+) iddia kosturuldu, (\d+) KIRMIZI\.$", re.M)


def ayna_kur(hedef):
    """tools/ + .github/workflows/ tam kopya. Symlink IZLENIR (fiziksel kopya)."""
    os.makedirs(hedef)
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(hedef, "tools"),
                    symlinks=False)
    shutil.copytree(os.path.join(ROOT, ".github", "workflows"),
                    os.path.join(hedef, ".github", "workflows"), symlinks=False)
    return hedef


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod):
    """Mutasyonu METNE uygular. Dayanak yoksa/coklu ise HARNESS BAYATTIR -> gurultulu
    duser; 'olctum' deyip hicbir sey olcmemek en kotu haldir."""
    metin = pristine
    for bul, yerine in degisimler:
        n = metin.count(bul)
        if n != 1:
            raise SystemExit(
                "🔴 HARNESS BAYAT (%s): dayanak metin %d kez bulundu (1 olmali).\n"
                "   Aranan: %r" % (kod, n, bul[:160]))
        metin = metin.replace(bul, yerine, 1)
    return metin


def kos(ayna, metinler):
    """Aynadaki kapiyi `--kendini-test` ile kostur -> (rc, iddia, kirmizi, kuyruk)."""
    for rel, metin in metinler.items():
        with open(os.path.join(ayna, rel), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, KAPI), "--kendini-test"],
                       cwd=ayna, capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    kirmizi = int(m.group(2)) if m else None
    return r.returncode, iddia, kirmizi, cikti[-3000:]


def main():
    print("SINYAL AYRIMI (yayin sagligi ↔ D1 sapmasi) — CURUTME KOSUMU")
    print("hedefler: %s\n" % ", ".join(HEDEFLER))
    once = {y: sha(y) for y in DOKUNULMAZ}

    pristine = {}
    for kod, _a, hedef, _d, _k in MUTANTLAR:
        if hedef in pristine:
            continue
        yol = os.path.join(ROOT, hedef)
        if not os.path.exists(yol):
            raise SystemExit("🔴 HARNESS BAYAT (%s): hedef dosya YOK: %s" % (kod, hedef))
        with open(yol, encoding="utf-8") as f:
            pristine[hedef] = f.read()
    # KAPI mutasyona ugramaz ama aynaya AYNEN yazilmali (kos() metinleri diske basar).
    with open(os.path.join(ROOT, KAPI), encoding="utf-8") as f:
        pristine.setdefault(KAPI, f.read())

    tmp = tempfile.mkdtemp(prefix="d1-sapma-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (canli kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, t_kuyruk = kos(ayna, dict(pristine))
        if not check("taban YESIL (cikis 0, kirmizi iddia 0)",
                     t_rc == 0 and t_kirmizi == 0,
                     "cikis=%s kirmizi=%s" % (t_rc, t_kirmizi)):
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi", t_iddia is not None, "iddia=%s" % t_iddia)
        print("   taban iddia sayisi: %s" % t_iddia)

        print("\n2) MUTANTLAR")
        for kod, aciklama, hedef, degisimler, kirmizi_bekleniyor in MUTANTLAR:
            metinler = dict(pristine)
            metinler[hedef] = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, metinler)
            print("\n  %s [%s] %s" % (kod, os.path.basename(hedef), aciklama))
            ok_sayi = check("%s: iddia sayisi KORUNDU (cokme kirmizisi DEGIL)" % kod,
                            iddia == t_iddia, "taban=%s mutant=%s" % (t_iddia, iddia))
            if kirmizi_bekleniyor:
                ok = check("%s: mutant OLDU (cikis != 0 ve kirmizi iddia > 0)" % kod,
                           rc != 0 and (kirmizi or 0) > 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
            else:
                ok = check("%s: KONTROL — mutant YESIL kaldi (gurultu yok)" % kod,
                           rc == 0 and kirmizi == 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
            if not (ok and ok_sayi):
                print("  --- kuyruk ---\n%s" % kuyruk)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n3) CANLI KAYNAKLAR DEGISMEDI MI")
    for y in DOKUNULMAZ:
        check("sha256 ayni: %s" % os.path.relpath(y, ROOT), sha(y) == once[y])

    oldurucu = sum(1 for m in MUTANTLAR if m[4])
    kontrol = len(MUTANTLAR) - oldurucu
    print("\nOZET: %d oldurucu + %d kontrol mutanti · %d kusur"
          % (oldurucu, kontrol, len(FAILS)))
    if FAILS:
        print("🔴 CURUTME KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ CURUTME GECTI — sessizlestirme (S1/S2/S9/S10/S12), cron `exit 1` dusurmesi "
          "(S3), hal yigma (S4/S5), yayin yoluna sizdirma (S6), kol bayragi dusurme/"
          "tersine cevirme (S7/S8) ve ters sizinti (S11) TEK TEK KIRMIZI yandi; "
          "yorum/adim-adi kontrolleri (K1/K2/K3) YESIL kaldi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
