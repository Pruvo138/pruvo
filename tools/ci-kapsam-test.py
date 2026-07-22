#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI KAPSAM KAPISI — her kabul testi ya CI'da kosuluyor ya da GEREKCELI olarak muaf.

NEDEN VAR (denetim, 20 Tem): .github/workflows/deploy.yml uzun sure YALNIZ 2 test kosuyordu
(kisisel-veri + kategori-parite). Repodaki onlarca kabul testi hicbir push'ta kosmadigi icin
"olu nobetci" bir test CI'dan YESIL/success alarak gecebiliyordu (B paketi olu sepet nobetcisi
son 4 kosumda success aldi). Bu kapi FAIL-CLOSED bir kapsam bekcisidir: repoda IZLENEN
(git ls-files) her kabul-testi dosyasi ya deploy.yml'de FIILEN kosulur, ya da asagidaki
IZIN_LISTESI'nde GEREKCE ile muaf tutulur. Ucuncu bir hal yoktur -> yeni bir test sessizce
CI-disi kalamaz.

KESIF (discovery) — git ls-files uzerinden (CI checkout == yerel; os.walk kullanılmaz cunku
gitignore'lu/uretilmis dosyalar yerelde gorunup CI'da gorunmez, sapma yaratirdi):
  * tools/  (arsiv/ HARIC):  <ad>-test.(py|js)  VEYA  test-<ad>.(py|js)  VEYA  <ad>-kapisi.py
    (META-DELIK ONARIMI, 21 Tem: kesif uzun sure yalniz "-test"/"test-" adlarina bakiyordu ->
     ADI "-kapisi.py" olan NOBETCILER — odeme-beyani-kapisi, landing-hukuk-kapisi,
     enjeksiyon-kapisi ... — kesfe HIC girmiyordu. Sonuc: biri deploy.yml'den silinse bu kapi
     UYARMAZ, YESIL kalirdi; olculdu: "run: python3 tools/odeme-beyani-kapisi.py" satiri
     silinmis mutant deploy.yml'de kapi eski desenle exit 0 veriyordu. Artik kapsam kurali
     nobetcilere de uygulanir.)
  * shop/test, onizleme/test, jenerator/test:  o dizinin DOGRUDAN altindaki .py/.js/.mjs/.cjs
    (alt dizinler — jenerator/test/aileler, esleme — fikstur/aile verisi, kosulabilir suite degil)

KABUL (bu dosyanin kendi kabul testleri):
  1. IZLENEN her kabul testi ya kosuluyor ya IZIN_LISTESI'nde -> degilse exit 1 (KAPSAMSIZ).
  2. IZIN_LISTESI'nde GEREKCESIZ (bos) giris -> exit 1.
  3. IZIN_LISTESI'nde olup artik KESFEDILMEYEN (silinmis/yeniden adlandirilmis) giris -> exit 1
     (liste curumesin).
  4. IZIN_LISTESI'nde olup AYNI ZAMANDA deploy.yml'de kosulan giris -> exit 1 (bayat muafiyet;
     kosuluyorsa listeden cikarilmali).
KIRMIZI-MUTASYON: deploy.yml'den bir "python3 tools/<x>-test.py" satiri silinirse o test
kapsamsiz kalir -> kapi KIRMIZI (exit 1). (--deploy <yol> ile alternatif/mutasyonlu bir kopyaya
isaret ederek GERCEK deploy.yml'e dokunmadan kanitlanabilir.)

Kullanim:
    python3 tools/ci-kapsam-test.py
    python3 tools/ci-kapsam-test.py --deploy /gecici/mutant-deploy.yml
"""
import argparse
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEPLOY_VARSAYILAN = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# ---- KESIF PREDIKATLARI ----------------------------------------------------
TOOLS_PAT = re.compile(
    r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js)|[^/]*-kapisi\.py)$")
DIR_PAT = re.compile(r"^(?:shop/test|onizleme/test|jenerator/test)/[^/]+\.(?:py|js|mjs|cjs)$")


def kesfet():
    """git ls-files uzerinden IZLENEN kabul-testi dosyalarini (repo-rel yol) dondur."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    bulunan = []
    for yol in r.stdout.splitlines():
        if yol.startswith("tools/arsiv/"):
            continue
        if TOOLS_PAT.match(yol) or DIR_PAT.match(yol):
            bulunan.append(yol)
    return sorted(bulunan)


def _icra_komutlari(deploy_metin):
    """deploy.yml'de FIILEN kosan komut govdelerini (satir satir) dondur.
    Yorum satirlari (strip -> '#') ELENIR; 'run:' oneki soyulur; boylece elde
    kalan metin yalniz gercekten calisan kabuk komutudur. Bir 'python3 <yol>'
    mensiyonu YORUM icinde ya da echo-string icinde geciyorsa bu listede komutun
    BASINDA yer almaz -> kosulan() onu 'kosuluyor' saymaz."""
    komutlar = []
    for ham in deploy_metin.splitlines():
        s = ham.strip()
        if not s or s.startswith("#"):
            continue  # bos satir ya da YAML yorumu -> icra degil
        if s.startswith("run:"):
            s = s[4:].strip()  # inline 'run: <komut>' ya da blok basi 'run: |'
        if s:
            komutlar.append(s)
    return komutlar


def kosulan(deploy_metin, kesif):
    """deploy.yml'de FIILEN ICRA edilen (kosulan) kesif dosyalarini dondur.

    BULGU 1 + T7 (curutucu/olcum kanitladi): eski regex TUM metni tariyordu ->
    bir YORUM / step-name / echo-string'de gecen ad da 'kosuluyor' sayiliyordu;
    biri 'run: python3 tools/x-test.py' satirini silip yerine '# python3
    tools/x-test.py' yorumu birakinca kapi SAHTE-YESIL kaliyordu (olu nobetci
    CI'dan success gecerdi). 072c0294 eslesmeyi 'python3 <yol>' on-ekine daraltti
    ama YORUM SATIRLARINI hala eliyordu degil -> python3 onekli bir yorum yine
    eslesiyordu. FIX: eslesmeyi GERCEK KOMUT GOVDESINE ve komutun BASINA capala
    (_icra_komutlari yorumlari eler, 'run:' onekini soyar). Negatif ileri-bakis
    (?![\\w./-]): uzun bir baska yolun on-eki olarak yanlis eslesmesin."""
    kos = set()
    komutlar = _icra_komutlari(deploy_metin)
    for yol in kesif:
        onek = re.compile(r"^python3\s+" + re.escape(yol) + r"(?![\w./-])")
        if any(onek.match(k) for k in komutlar):
            kos.add(yol)
    return kos


# T8: kosulan()'in capasina uyan "bare" form — komut govdesi 'python3 <duz-gorece-yol>'
# ile baslar (yol '-' bayragiyla, './' ile ya da '/' tam-yolla BASLAMAZ).
SAYILABILIR_PY3 = re.compile(r"^python3\s+[A-Za-z0-9_][\w./-]*(?:\s|$)")


def sayilamayan_python3(deploy_metin):
    """T8 GELECEK-ROBUSTLUK UYARISI (BLOKLAMAZ — exit kodunu ETKILEMEZ).

    T7 capasi ('^python3 <yol>') su GERCEK-ICRA formlarini SAYAMAZ: 'env X=1 python3 ...',
    'cd x && python3 ...', 'python3 -X utf8 tools/x.py' (bayrak araya), 'python3 ./tools/x.py',
    '/usr/bin/python3 ...'. Cari deploy.yml'de hepsi bare form (18/18, olculdu T8) -> cari
    sorun YOK. RISK: gelecekte biri kapiyi bu formlarla eklerse kosulan() onu 'kosulmuyor'
    sanir -> YANLIS-POZITIF KIRMIZI tum yayini durdurur ve kapi suclanir. Bu fonksiyon
    _icra_komutlari()'ndan gecen (YORUM OLMAYAN) satirlarda 'python3' gecen ama bare capaya
    uymayan satirlari dondurur; main() bunlari BLOKLAMAYAN uyari olarak basar."""
    supheli = []
    for k in _icra_komutlari(deploy_metin):
        if "python3" not in k:
            continue
        if SAYILABILIR_PY3.match(k):
            continue
        supheli.append(k)
    return supheli


# ---- GEREKCE SABITLERI -----------------------------------------------------
R_AYRI = ("Ayri alt-proje/dagitim hedefi (shop=Cloudflare Worker, onizleme, jenerator kendi "
          "harness'i). Bu is akisi YALNIZ GitHub Pages site build'i; bu suite o projenin CI "
          "hattinda kosulur, Pages job'una girmez.")
R_NODE = ("CI build job'u Python-only (setup-node yok) -> JS/Node suite'i kosamaz. Ayri bir "
          "node job'u gerekir (RAPOR onerisi).")
R_AG = ("Ag/uzak platform erisimi gerektirir (parite CDN'e vurur) -> CI'da deterministik degil; "
        "ag-izinli ayri adim gerekir (RAPOR onerisi).")
R_YOL = ("Mimar-disiplin kapisi: mutlak /Users/okan/dev/pruvo yoluna VE commit EDILMEYEN "
         ".claude/settings.json + .git/hooks kablolamasina bagli -> GitHub fresh checkout'ta "
         "yapisal olarak KIRMIZI. Yerel gelistirici disiplini araci, deploy CI adimi degil.")
R_YAVAS = ("Yerelde >30s (build+ag ya da mutasyon harness) -> tek build job'unu blokar; "
           "izole/ayri job olmadan Pages hattina alinmaz (RAPOR onerisi).")
R_SONRA = ("Offline + yerelde YESIL, ama Paket C kapsami YALNIZ mimarin verdigi cekirdek "
           "eklemeleri CI'ya aldi. Bu test sonraki turda (ubuntu path/env dogrulamasi sonrasi) "
           "CI'ya alinabilir — kod-kilidi ornegi 'yerel-yesil / CI-kirmizi' tuzagini kanitladi, "
           "o yuzden kor-ekleme yapilmadi.")
R_HOOK = ("Claude Code PreToolUse KANCASI, kosulabilir kabul testi DEGIL: stdin'den JSON alir, "
          "karar objesi dondurur (argumansiz kosunca girdi yok -> exit 0, hicbir sey kanitlamaz). "
          "Yerel ajan disiplin cihazi; GitHub Pages build'inde karsiligi yok.")
R_GIZLI = ("Gizli/izlenmeyen girdiye bagli: .urun-kaynaklari.json (gitignore) + working-tree'de "
           "stage'lenmis PARTI farki. CI fresh checkout'unda ikisi de YOK -> kapi bos parti "
           "gorup anlamsiz YESIL yakar (sahte nobetci). Urun-ekleme hattinda (MaCiT) yerel "
           "kosulur; deploy hattinin girdisi degil.")
R_TASARIM = ("TASARIM GEREGI yayin-disi (kendi dosyasindaki not): 'bu kapi build.py'ye BAGLANMAZ "
             "— tek kotu kategori TUM yayini kirmasin'. Kategori drifti urunu katalogda birakir, "
             "yalniz filtreden dusurur; yayini bloklamak orantisiz. Bagimsiz calistirilabilir "
             "kabul testi olarak yerelde/duzeltme akisinda kosulur.")
R_YEREL_HIJYEN = ("Yerel calisma-agaci hijyeni: .gitignore blogunun CONTENT_PAGES ile ortusmesini "
                  "denetler. Drift CI'da GORUNMEZ (uretilen dizinler fresh checkout'ta yok) ve "
                  "canli siteyi bozmaz — yalniz gelistiricinin `git status`ini kirletir/kazara "
                  "commit riski dogurur. Yayini bloklamasi orantisiz; commit oncesi yerel kapi.")
R_FTS5 = ("Yerel fts5-trigram sqlite gerektirir (sema-yukleme adiminda CREATE VIRTUAL TABLE ... "
          "USING fts5(tokenize='trigram')). CI ubuntu stok sqlite3'unde fts5-trigram tokenizer'i "
          "yok -> test daha sema yuklerken patlar (yerel-yesil / CI-kirmizi). R_YAVAS/R_YOL ile "
          "ayni sinif: yapisal olarak CI-disi, deploy.yml'e EKLENMEZ; canli D1 dogrulamasi ayri "
          "go-live fazinda yapilir.")

# ---- IZIN LISTESI (muaf test -> GEREKCE). Bos gerekce = exit 1. ----------
IZIN_LISTESI = {
    # --- Ayri dagitim hedefleri (shop / onizleme / jenerator) ---
    "shop/test/eposta.mjs": R_AYRI,
    "shop/test/kabul.js": R_AYRI,
    "shop/test/olcum-kapisi.cjs": R_AYRI,
    "shop/test/olcum.mjs": R_AYRI,
    "shop/test/ref-route.mjs": R_AYRI,
    "shop/test/sepet-panel.js": R_AYRI,  # B paketi YESILLEDI; shop ayri Worker hedefi (kardesleri gibi)
    "onizleme/test/eslem-olcum.py": R_AYRI,
    "onizleme/test/kabul.js": R_AYRI,
    "onizleme/test/kapi1.js": R_AYRI,
    "jenerator/test/birlestir.py": R_AYRI,
    "jenerator/test/dogrula.py": R_AYRI,
    "jenerator/test/fiyat-tablosu-uret.py": R_AYRI,
    "jenerator/test/fiyat-test.js": R_AYRI,
    "jenerator/test/hacim-eval.js": R_AYRI,
    "jenerator/test/kabul.py": R_AYRI,
    "jenerator/test/kalibrasyon-referans-uret.py": R_AYRI,
    "jenerator/test/kalibrasyon-senkron.js": R_AYRI,
    "jenerator/test/stl_hacim.py": R_AYRI,
    "jenerator/test/vida-referans-uret.py": R_AYRI,
    "jenerator/test/vitrin-kabul.js": R_AYRI,
    # --- tools/ JS (CI'da node yok) ---
    "tools/attribution-ref-test.js": R_NODE,
    "tools/marka-limit-test.js": R_NODE,
    "tools/riza-tikkimligi-test.js": R_NODE,
    "tools/parite-test.js": R_AG,
    "tools/url-senkron-test.js": R_NODE,  # E paketi YESILLEDI; JS suite, CI'da node yok
    # --- tools/ python: mimar-disiplin (mutlak yol + commit'siz kablolama) ---
    "tools/mimar-kilit-test.py": R_YOL,
    "tools/mimar-commit-kapisi-test.py": R_YOL,
    "tools/mimar-kapi-mutasyon-test.py": R_YOL,
    "tools/kapi-envanteri-test.py": R_YOL,
    "tools/kod-kilidi-test.py": R_YOL,  # E paketi YESILLEDI; mutlak /Users/okan/dev/pruvo yoluna bagli -> fresh checkout'ta yapisal KIRMIZI
    # --- tools/ NOBETCILER (*-kapisi.py) — kesif 21 Tem genisletildi, CI'da kosmayanlar ---
    "tools/komut-stili-kapisi.py": R_HOOK,
    "tools/mimar-icra-kapisi.py": R_HOOK,
    "tools/mimar-commit-kapisi.py": (
        R_HOOK + " Ayrica git commit backstop'u olarak commit EDILMEYEN .git/hooks kablolamasina "
        "ve ana-checkout/worktree ayrimina bagli (R_YOL ile ayni sinif)."),
    "tools/denetim-kapisi.py": R_GIZLI,
    "tools/kategori-kapisi.py": R_TASARIM,
    "tools/gitignore-kapisi.py": R_YEREL_HIJYEN,
    "tools/regresyon-kapisi.py": (
        R_YOL + " Ek olarak varsayilan suite'i node tools/parite-test.js + parite-ege.js icerir "
        "(CI'da node YOK + ag gerekir, R_NODE/R_AG) ve kapsadigi testler zaten tek tek bu "
        "listede muhasebeli -> CI'da kosmasi cift-sayim olurdu."),
    # --- tools/ python: yavas/harici (>30s) ---
    "tools/feed-cache-bust-test.py": (
        R_YAVAS + " OLCULDU (F2 raporu): test build.py'yi 2 KEZ kosuyor -> tek build 108,0 s, "
        "test toplam 227,9 s (mutasyon kosumlarinda 148-302 s). Tek build job'una ~4-5 dk "
        "eklerdi, kendisi de deploy'un ZATEN kosturdugu build.py'nin ciktisini yeniden uretir. "
        "CI'YA ALINMA KOSULU (RAPOR onerisi): test build.py'yi alt-surec olarak degil "
        "render_merchant_feed'i import edip 2 kez cagirarak kosarsa sure saniyeye iner ve "
        "bloklayici adim olarak eklenebilir."),
    "tools/filament-test.py": R_YAVAS,
    "tools/kaynak-akis-test.py": R_YAVAS,
    "tools/test-bbox-3mf.py": R_YAVAS,
    # --- tools/ python: fts5-trigram sqlite gerektiren (CI ubuntu'da yok) ---
    "tools/taban-fiyat-d1-test.py": R_FTS5,
    # --- tools/ python: offline-yesil, sonraki turda alinabilir ---
    "tools/d1-sync-durum-test.py": R_SONRA,
    "tools/denetim-kapisi-test.py": R_SONRA,
    "tools/derin-cap-test.py": R_SONRA,
    "tools/durum-edge-test.py": R_SONRA,
    "tools/durum-test.py": R_SONRA,
    "tools/gorsel-anahtar-test.py": R_SONRA,
    "tools/gorsel-kapisi-test.py": R_SONRA,
    "tools/kaynak-entegrasyon-test.py": R_SONRA,
    "tools/lisans-havuz-test.py": R_SONRA,
    "tools/makerworld-ara-test.py": R_SONRA,
    "tools/makerworld-lisans-test.py": R_SONRA,
    "tools/marka-filtre-test.py": R_SONRA,
    "tools/meta-piksel-test.py": R_SONRA,
    "tools/olculmemis-siparis-test.py": R_SONRA,
    "tools/printables-lisans-test.py": R_SONRA,
    "tools/siparisler-test.py": R_SONRA,
    "tools/surum-test.py": R_SONRA,
    "tools/test-baski-senkron.py": R_SONRA,
    "tools/test-merchant-feed.py": R_SONRA,
    "tools/thing-codex-test.py": R_SONRA,
    "tools/thingiverse-gallery-test.py": R_SONRA,
    "tools/yargi-firearm-test.py": R_SONRA,
    "tools/yazdir-test.py": R_SONRA,
}


def bulgu1_mutasyon_kontrol():
    """BULGU 1 KALICI MUTASYON NOBETCISI (curutucu kanitladi):
    Bir testin 'run: python3 <yol>' ICRA satiri deploy.yml'den silinip ADI yalniz bir
    YORUM/step-name'de kalirsa, kosulan() o testi 'kosuluyor' SAYMAMALIDIR. Eski regex tum
    metni tariyordu -> yalniz-yorum mensiyonu sahte-yesil yapiyordu (olu nobetci CI'dan
    success gecerdi). Bu kontrol GERCEK deploy.yml'den mutant uretir (ci-kapsam-test.py'nin
    run satirini siler, yorum mensiyonu birakir) ve iki sarti dogrular:
      + POZITIF: gercek deploy o yolu SAYAR (run: ile gecer).
      + MUTASYON: yalniz-yorum mutanti o yolu SAYMAZ.
    T7 EKI: ikinci mutant, run satirini python3-onekli bir YORUMA cevirir
    ('# python3 <yol>') ve o yolun SAYILMADIGINI dogrular -> yorum-bypass
    (olculdu: B/C/D/E/F kanaryalari) geri gelirse KIRMIZI yanar.
    (ok, hata_satirlari) dondurur."""
    hedef = "tools/ci-kapsam-test.py"
    run_satir = "        run: python3 %s\n" % hedef
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()
    if run_satir not in gercek:
        return False, ["beklenen icra satiri gercek deploy.yml'de yok: %r "
                       "(cagri bicimi degistiyse bu nobetciyi guncelle)" % run_satir]
    mutant = gercek.replace(run_satir, "", 1)
    if hedef not in mutant:
        return False, ["mutantta yorum mensiyonu kalmadi -> mutasyon testi anlamsiz "
                       "(deploy.yml yorumu %s'yi artik anmiyor)" % hedef]
    # T7 kanaryasi: run satiri python3-onekli YORUMA cevrilmis mutant (icra edilmez)
    yorum_mutant = gercek.replace(run_satir, "        # python3 %s\n" % hedef, 1)
    kesif = kesfet()
    if hedef not in kesif:
        return False, ["%s kesif predikatiyla bulunamadi (predikat bozulmus)" % hedef]
    hata = []
    if hedef not in kosulan(gercek, kesif):
        hata.append("POZITIF KONTROL BASARISIZ: gercek deploy.yml %s'yi kosulan saymadi" % hedef)
    if hedef in kosulan(mutant, kesif):
        hata.append("BULGU 1 GERI GELDI: run satiri silinip yalniz yorumda kalan %s "
                    "hala 'kosuluyor' sayildi (regex icra baglamina daralmali)" % hedef)
    if hedef in kosulan(yorum_mutant, kesif):
        hata.append("T7 YORUM-BYPASS GERI GELDI: run satiri '# python3 <yol>' yorumuna "
                    "cevrilince %s hala 'kosuluyor' sayildi (yorum satirlari elenmeli)" % hedef)
    return (not hata), hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", default=DEPLOY_VARSAYILAN,
                    help="deploy.yml yolu (kirmizi-mutasyon icin alternatif kopya verilebilir)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ BULGU 1 mutasyon nobetcisini kosar (gercek deploy.yml uzerinden)")
    args = ap.parse_args()

    if args.kendini_test:
        ok, hata = bulgu1_mutasyon_kontrol()
        print("BULGU 1 MUTASYON NOBETCISI")
        if ok:
            print("  ✅ gercek deploy sayiyor; yalniz-yorum mutanti saymiyor")
            print("SONUC: YESIL ✅")
            return 0
        for h in hata:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌")
        return 1

    if not os.path.exists(args.deploy):
        sys.exit("deploy.yml bulunamadi: " + args.deploy)
    with open(args.deploy, encoding="utf-8") as f:
        deploy_metin = f.read()

    kesif = kesfet()
    kos = kosulan(deploy_metin, kesif)
    kesif_kume = set(kesif)

    # T8: bloklamayan gelecek-robustluk uyarisi (hatalar listesine GIRMEZ, exit degismez).
    for satir in sayilamayan_python3(deploy_metin):
        print("UYARI: python3 iceren ama sayilamayan icra satiri "
              "(bare 'python3 tools/x.py' formu kullan): %s" % satir)

    hatalar = []

    # 2) gerekcesiz izin girisi
    for yol, gerekce in IZIN_LISTESI.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ izin girisi (bos gerekce): %s" % yol)

    # 3) bayat izin: kesfedilmeyen (silinmis/yeniden adlandirilmis) yol
    for yol in IZIN_LISTESI:
        if yol not in kesif_kume:
            hatalar.append("BAYAT izin (artik kesfedilmiyor — sil ya da yolu duzelt): %s" % yol)

    # 4) bayat izin: hem izinde hem kosuluyor
    for yol in IZIN_LISTESI:
        if yol in kos:
            hatalar.append("BAYAT izin (test ARTIK KOSULUYOR — izinden cikar): %s" % yol)

    # 1) kapsamsiz: kesfedilmis ama ne kosuluyor ne izinli
    kapsamsiz = []
    for yol in kesif:
        if yol in kos:
            continue
        if yol in IZIN_LISTESI:
            continue
        kapsamsiz.append(yol)
    for yol in kapsamsiz:
        hatalar.append("KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % yol)

    # 5) BULGU 1 mutasyon nobetcisi — yalniz GERCEK deploy.yml'e karsi (mutant --deploy
    #    verildiginde pozitif kontrol anlamsiz olur, o yuzden atla).
    mutasyon_hata = []
    if os.path.abspath(args.deploy) == os.path.abspath(DEPLOY_VARSAYILAN):
        ok, mutasyon_hata = bulgu1_mutasyon_kontrol()
        for h in mutasyon_hata:
            hatalar.append("BULGU1-MUTASYON: " + h)

    # ---- rapor ----
    muaf = [y for y in kesif if y not in kos]
    print("CI KAPSAM KAPISI")
    print("  Kesfedilen kabul testi : %d" % len(kesif))
    print("  deploy.yml'de kosulan  : %d  (%s)" % (
        len(kos), ", ".join(sorted(kos)) or "-"))
    print("  Muaf (izin listesi)    : %d" % len(muaf))
    print("-" * 70)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 70)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    print("SONUC: YESIL ✅  — her kabul testi ya kosuluyor ya gerekceli muaf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
