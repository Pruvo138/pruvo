#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onizleme derleme paketini toplar ve GIZLI R2 bucket'ina yukler.

PAKET = eslem-ozel.json + eslemin isaret ettigi .scad kaynaklari. Ikisi de SIRDIR
(uyelik ureteci kodu/degisken adlari) — public repoya ASLA girmez (gitignore).
Kanonik kopya R2 `pruvo-ozel` bucket'i: CI imaj derlerken oradan ceker
(.github/workflows/onizleme-imaj.yml), boylece sir GitHub'a ugramaz.

PAKETE AYRICA BIZIM ureteclerimiz girer (ACIK_AILELER): pruvo-jenerator .scad'lari
tedarikci kodu DEGILDIR, eslemleri PUBLIC jenerator/test/esleme/ dosyalarindan
uretilir (tek kaynak — test ile onizleme eslemi ayrisamaz). Bu aileler icin sir
katmani yoktur; paket ici eslem dosyasina derleme aninda birlestirilirler.

Kaynaklar (SALT OKUNUR — ana repoya hicbir sey yazilmaz):
  - eslem: <repo>/onizleme/derleyici/eslem-ozel.json (gitignore'lu yerel dosya)
  - .scad: PRUVO_UYELIK_DIR (varsayilan /Users/okan/dev/pruvo/.uyelik-kodlar)
  - bizim .scad: PRUVO_JENERATOR_DIR (vars. ~/dev/pruvo-jenerator/jeneratorler)

SURUMLU ANAHTAR (Okan/mimar karari 29 Tem 2026 — UZERINE YAZMA TERK EDILDI):
  Bu betik YALNIZ surumlu anahtara yazar: onizleme/paket-v<N>.tar.gz. Sabit "guncel"
  takma adina yazma KALDIRILDI. Sebep olculdu: R2'de ONCEDEN VAR OLAN bir anahtarin
  uzerine `wrangler r2 object put` "Upload complete." + RC=0 basiyor ama nesne
  DEGISMIYOR (4 ayri deneme, sha256 birebir ayni); YENI anahtar aninda yaziliyor.
  Depo kurali zaten ayni yone isaret ediyordu ("ayni R2 anahtarinin uzerine YAZMA ->
  yeni dosya adi"). CI cektigi anahtari artik workflow_dispatch girdisiyle alir
  (.github/workflows/onizleme-imaj.yml -> inputs.paket_anahtar).
  NOBETCI: tools/paket-tazelik-kapisi.py surumlu_anahtar_nobeti (bloklayici, deploy.yml).

Kullanim:
  python3 tools/onizleme-paket-yukle.py --yerel <dizin>   # sadece topla (test/kabul icin)
  python3 tools/onizleme-paket-yukle.py                   # topla + R2'ye yukle
Yukleme yerel wrangler oturumuyla yapilir (token gerekmez):
  npx wrangler r2 object put pruvo-ozel/onizleme/paket-v<N>.tar.gz --file ...
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESLEM_YOL = os.path.join(REPO, "onizleme", "derleyici", "eslem-ozel.json")
BUCKET = "pruvo-ozel"

# PARCA (COK GOVDELI URUN) AYIRACI — 2-renk yazi sozlesmesi, 29 Tem 2026.
# Bir aile birden fazla BASILABILIR GOVDE dondurebilir (or. cerceve: gövde + yazı,
# AMS 2 filaman). Her govde derleyicide AYRI bir eslem ailesi olarak durur:
#   "<urunId>#<parca>"  ->  ayni .scad, ayni -D bayraklari, YALNIZ `Output` farkli.
# TABAN AILE (parcasiz "<urunId>") BIREBIR AYNI KALIR: eski tek-govde cagrilari
# bit-ayni cikti verir (geriye donuk uyumluluk yapisal, kosula bagli degil).
# Ayirac urun id'lerinde KULLANILMAYAN bir karakter olmalidir (id'ler kebab-case).
PARCA_AYIRAC = "#"

# BIZIM ureteclerimiz (pruvo-jenerator v2): aile-id -> public test eslem adi.
# Eslem tek kaynagi jenerator/test/esleme/<ad>.json (dogrula.py ile ayni dosya).
ACIK_AILELER = {
    "olcuye-ozel-baglanti-konektor": "konektor",
    "olcuye-ozel-montaj-braketi": "braket",
    "ozel-disli-kramayer-uretimi": "disli",
    # Yeni sari aileler 1. dalga (2026-07-17) — bizim ureteclerimiz
    "olcuye-ozel-hortum-adaptoru": "adaptor",
    "olcuye-ozel-kutu-organizer": "kutu",
    "olcuye-ozel-vidali-kavanoz-tapa": "kavanoz",
    # Olcuye ozel toka (2026-07-26) — bizim uretecimiz (jeneratorler/toka.scad)
    "olcuye-ozel-toka": "toka",
    # Olcuye ozel cerceve (2026-07-28) — bizim uretecimiz (jeneratorler/cerceve.scad).
    # Eslem public jenerator/test/esleme/cerceve.json'dan turer: 5 geometri parametresi
    # (acilik_eni/boyu, kenar_genisligi, derinlik, kenar_stili) + MUSTERI YAZISI
    # (yazi -> Caption_Text, `metin` blogu) + Output="frame".
    # 🔴 GUNCELLEME 2026-07-29 (Okan karari — ONCEKI NOT BAYATTI): eski not "yazi
    # onizleme kapsaminda DEGIL, Caption_Text='' sabit" diyordu. O kapsam-disi karari
    # KALDIRILDI: onizleme musterinin girdigi metni GOSTERIR ve ayni eslem uretimi de
    # besler (onizleme ile /ic-derle AYNI derleyiciyi kullanir, onizleme/src/index.js).
    # 🔴 GUNCELLEME 2026-07-29 (2. tur): 2-RENK caption akisi ARTIK KAPSAM ICINDE.
    # `parcalar` blogu (jenerator/test/esleme/cerceve.json) iki EK eslem ailesi uretir:
    #   olcuye-ozel-cerceve#govde -> Output="frame_no_caption" (yazisiz cerceve kabugu)
    #   olcuye-ozel-cerceve#yazi  -> Output="caption"          (yalniz kabartma yazi)
    # Taban aile (Output="frame", tek govde) AYNEN durur. Bkz. parca_bloklari().
    "olcuye-ozel-cerceve": "cerceve",
}


def acik_eslem_uret(ad):
    """jenerator/test/esleme/<ad>.json -> server.py eslem blogu.
    Sayi parametreleri katsayi-1 dogrusal terim, secim parametreleri
    deger_esleme tablosu (yoksa kimlik tablosu), METIN parametreleri
    server.py'nin `metin` blogu, sabitler aynen.

    METIN DALI (2026-07-29, kalici onarim): eskiden yalniz `sayi`/`secim`
    biliniyordu ve `metin` tipi sys.exit ile REDDEDILIYORDU. Bu YAPISAL ENGEL
    yuzunden cerceve ailesinde musteri yazisi eslemeye konamamis, `sabit`e
    Caption_Text="" yazilarak bypass edilmisti -> musteri ne yazarsa yazsin
    uretilen STL AYNI cikiyordu (canli olcum 29 Tem: '' / 'OKAN' / 'ZZZZZZZZ'
    ucu de 65284 bayt, 1304 ucgen, ayni SHA-256). Sunucu tarafi `metin` blogunu
    ZATEN destekliyordu (onizleme/derleyici/server.py blok_uygula): SIKI beyaz
    liste + METIN_SERT_TAVAN(24) + d_deger tirnak savunmasi. Burada YENI bir
    guvenlik yuzeyi ACILMAZ — yalnizca {"param": <sema_param>} baglantisi
    uretilir, temizlik/tavan/kacis tamamen sunucuda kalir.
    NOBETCI: tools/metin-eslem-test.py (metin parametresi olan her aile icin
    iki farkli metin -> iki farkli -D bayrak kumesi)."""
    with open(os.path.join(REPO, "jenerator", "test", "esleme",
                           ad + ".json"), encoding="utf-8") as f:
        test_eslem = json.load(f)
    with open(os.path.join(REPO, "jenerator", "urunler",
                           test_eslem["urunId"] + ".json"), encoding="utf-8") as f:
        sema = json.load(f)
    tipler = dict((p["ad"], p) for p in sema["parametreler"])
    sayisal, secim, metin = {}, {}, {}
    deger_esleme = test_eslem.get("deger_esleme") or {}
    for param, scad_ad in (test_eslem.get("esleme") or {}).items():
        tanim = tipler.get(param)
        if tanim is None:
            sys.exit("%s: eslemdeki '%s' semada yok" % (ad, param))
        if tanim.get("tip", "sayi") == "sayi":
            sayisal[scad_ad] = {"terimler": {param: 1}}
        elif tanim["tip"] == "secim":
            tablo = deger_esleme.get(param)
            if tablo is None:  # kimlik: sema degerleri scad'a aynen gider
                tablo = dict((s["deger"] if isinstance(s, dict) else s,
                              s["deger"] if isinstance(s, dict) else s)
                             for s in tanim["secenekler"])
            secim[scad_ad] = {"param": param, "tablo": tablo}
        elif tanim["tip"] == "metin":
            metin[scad_ad] = {"param": param}
        else:
            sys.exit("%s: '%s' tipi (%s) onizlemeye eslenemez" %
                     (ad, param, tanim["tip"]))
    sabit = dict(test_eslem.get("sabit") or {})
    # FAIL-CLOSED: `sabit` blok_uygula'da EN SON uygulanir -> ayni scad degiskeni
    # hem `metin`de hem `sabit`te olursa sabit musteri metnini SESSIZCE EZER
    # (cerceve'de tam bu yasandi: Caption_Text sabit "" idi). Sessiz ezme yerine
    # paket uretimi durur.
    cakisan = sorted(set(metin) & set(sabit))
    if cakisan:
        sys.exit("%s: %s hem `metin` eslemesinde hem `sabit`te -> sabit musteri "
                 "metnini ezer; `sabit`ten CIKARIN" % (ad, ", ".join(cakisan)))
    ortak = {"sayisal": sayisal, "secim": secim, "sabit": sabit}
    if metin:
        # Metinsiz ailelerde anahtar HIC eklenmez -> uretilen paket eslemi bu
        # degisiklikten ONCEKIYLE BIREBIR AYNI kalir (yanlis-pozitif kapisi).
        ortak["metin"] = metin
    return test_eslem["urunId"], {
        "scad": test_eslem["scad"],
        "secici": None,
        "ortak": ortak,
        "varyantlar": None,
    }, test_eslem["scad"]


def parca_bloklari(ad, taban_blok):
    """jenerator/test/esleme/<ad>.json `parcalar` -> {"<urunId>#<parca>": blok}.

    NE YAPAR: taban ailenin blogunu KOPYALAYIP yalnizca `ortak.sabit` icindeki
    belirtilen anahtarlari degistirir (cerceve: Output frame -> frame_no_caption /
    caption). Boylece iki govde AYNI .scad'ten, AYNI -D bayraklariyla, TEK farkla
    uretilir -> HIZALAMA yapisal olarak garanti (ayni koordinat sistemi; ayrica
    cerceve.scad Caption_Fit="existing" oldugu icin dis olcu yazidan bagimsiz).

    FAIL-CLOSED kurallari (sessiz sapma yerine paket uretimi DURUR):
      * parca adi yalniz [a-z0-9-] olabilir (ayirac/yol karakteri anahtara sizmasin),
      * ezilen her SCAD degiskeni taban `sabit`te ZATEN VAR olmali (yazim hatasi
        yeni bir degisken ihdas edemez),
      * `metin`/`sayisal`/`secim` bloklari DEGISTIRILEMEZ (musteri metni ve olculer
        iki govdede AYRI olamaz — ayrisirsa yazi govdesi baska bir yaziyi basardi).
    `parcalar` yoksa BOS sozluk doner -> uretilen paket eslemi bu degisiklikten
    ONCEKIYLE BIREBIR AYNI kalir (yanlis-pozitif kapisi)."""
    with open(os.path.join(REPO, "jenerator", "test", "esleme",
                           ad + ".json"), encoding="utf-8") as f:
        test_eslem = json.load(f)
    parcalar = test_eslem.get("parcalar") or {}
    if not parcalar:
        return {}
    urun_id = test_eslem["urunId"]
    taban_sabit = (taban_blok.get("ortak") or {}).get("sabit") or {}
    cikti = {}
    for parca, ezme in sorted(parcalar.items()):
        if not parca or not all(c.islower() or c.isdigit() or c == "-" for c in parca):
            sys.exit("%s: gecersiz parca adi %r (yalniz kucuk harf/rakam/-)" % (ad, parca))
        if not isinstance(ezme, dict) or not ezme:
            sys.exit("%s: parca '%s' bos/gecersiz ezme" % (ad, parca))
        eksik = sorted(set(ezme) - set(taban_sabit))
        if eksik:
            sys.exit("%s: parca '%s' taban `sabit`te olmayan degisken(ler) eziyor: %s"
                     % (ad, parca, ", ".join(eksik)))
        blok = json.loads(json.dumps(taban_blok))     # derin kopya
        blok["ortak"]["sabit"] = dict(taban_sabit)
        blok["ortak"]["sabit"].update(ezme)
        cikti[urun_id + PARCA_AYIRAC + parca] = blok
    return cikti


def topla(hedef, uyelik_dir, jenerator_dir):
    if not os.path.exists(ESLEM_YOL):
        sys.exit("eslem-ozel.json yok: %s (gitignore'lu — R2'deki paketten geri alin: "
                 "npx wrangler r2 object get %s/onizleme/paket-v<N>.tar.gz)" %
                 (ESLEM_YOL, BUCKET))
    with open(ESLEM_YOL, encoding="utf-8") as f:
        eslem = json.load(f)
    os.makedirs(hedef, exist_ok=True)
    eksik = []
    for aile, tanim in eslem["aileler"].items():
        scadlar = {tanim["scad"]}
        for varyant in (tanim.get("varyantlar") or {}).values():
            if varyant and varyant.get("scad"):
                scadlar.add(varyant["scad"])  # cift-uretecli aile (vida, yay)
        for scad in sorted(scadlar):
            kaynak = os.path.join(uyelik_dir, scad)
            if not os.path.exists(kaynak):
                eksik.append("%s (%s)" % (scad, aile))
                continue
            shutil.copy2(kaynak, os.path.join(hedef, scad))
    if eksik:
        sys.exit("eksik .scad kaynagi: %s (PRUVO_UYELIK_DIR dogru mu?)" % ", ".join(eksik))
    # bizim uretecler: public eslemden uret + scad'i pruvo-jenerator'den kopyala
    for aile_id, ad in sorted(ACIK_AILELER.items()):
        urun_id, blok, scad = acik_eslem_uret(ad)
        if urun_id != aile_id:
            sys.exit("ACIK_AILELER tutarsiz: %s != %s" % (urun_id, aile_id))
        if aile_id in eslem["aileler"]:
            sys.exit("%s hem eslem-ozel.json'da hem ACIK_AILELER'de" % aile_id)
        eslem["aileler"][aile_id] = blok
        # COK GOVDELI aile (2-renk): "<aile>#<parca>" ek eslem girdileri. Taban aile
        # yukarida OLDUGU GIBI yazildi -> tek-govde yolu degismez.
        for parca_id, parca_blok in parca_bloklari(ad, blok).items():
            if parca_id in eslem["aileler"]:
                sys.exit("parca ailesi cakisti: %s" % parca_id)
            eslem["aileler"][parca_id] = parca_blok
        kaynak = os.path.join(jenerator_dir, scad)
        if not os.path.exists(kaynak):
            sys.exit("bizim .scad yok: %s (PRUVO_JENERATOR_DIR dogru mu?)" % kaynak)
        shutil.copy2(kaynak, os.path.join(hedef, scad))
    with open(os.path.join(hedef, "eslem-ozel.json"), "w", encoding="utf-8") as f:
        json.dump(eslem, f, ensure_ascii=False, indent=2)
    return eslem.get("surum", 1)


def _ozet(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def yuklenecek_anahtarlar(surum):
    """Bu surum icin R2'ye yazilacak anahtarlarin TAM listesi.

    SAF FONKSIYON — nobetci (tools/paket-tazelik-kapisi.py) bunu METIN ARAMADAN,
    dogrudan cagirip olcer: liste yalniz surumlu anahtar icermeli. Sabit bir takma
    ad ("guncel" gibi) geri eklenirse nobetci KIRMIZI yanar, cunku uzerine yazma
    bu bucket'ta SESSIZCE basarisiz oluyor (docstring'e bak)."""
    return ["onizleme/paket-v%d.tar.gz" % int(surum)]


def yukle_ve_dogrula(anahtar, arsiv, tmp):
    """R2'ye yaz + GERI OKUYUP dogrula. Basari damgasi wrangler'in cikis koduna DEGIL
    nesnenin GERCEK icerigine baglidir.

    NEDEN (olculdu 29 Tem 2026): `wrangler r2 object put` VAR OLAN bir anahtarin
    uzerine yazarken "Upload complete." basip 0 donduyu halde nesne DEGISMIYORDU.
    Somut: paket-v6.tar.gz (YENI anahtar) yazildi; ayni kosumdaki paket-guncel.tar.gz
    (VAR OLAN anahtar) 4 ayri denemede de v5 icerigiyle kaldi (SHA-256 birebir ayni).
    Kontrol: yeni anahtarlarda hem olusturma hem uzerine yazma ANINDA gorunuyor.
    Bu betik eskiden yalniz returncode'a bakiyordu -> "yuklendi" der, CI BAYAT paketi
    ceker, imaj eski eslemle derlenir ve hata CANLIDA ortaya cikardi (sessiz hata)."""
    komut = ["npx", "wrangler", "r2", "object", "put",
             BUCKET + "/" + anahtar, "--file", arsiv, "--remote"]
    proc = subprocess.run(komut, cwd=REPO, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout.decode("utf-8", "replace"))
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        sys.exit("R2 yuklemesi basarisiz: %s (wrangler oturumu acik mi?)" % anahtar)
    geri = os.path.join(tmp, "geri-" + anahtar.replace("/", "_"))
    kontrol = subprocess.run(
        ["npx", "wrangler", "r2", "object", "get", BUCKET + "/" + anahtar,
         "--file", geri, "--remote"], cwd=REPO, capture_output=True)
    if kontrol.returncode != 0 or not os.path.exists(geri):
        sys.exit("GERI OKUMA YAPILAMADI: %s -> yukleme DOGRULANMADI (yesil sayma)" % anahtar)
    bekleniyor, gelen = _ozet(arsiv), _ozet(geri)
    if bekleniyor != gelen:
        sys.exit(
            "🔴 SESSIZ YUKLEME HATASI: %s — wrangler basarili dedi ama R2'deki nesne "
            "DEGISMEDI (beklenen sha256 %s, R2'de %s). CI bu anahtari cektigi icin BAYAT "
            "paketle imaj derlenir. SEBEP: bu anahtar R2'de ZATEN VARDI (uzerine yazma bu "
            "bucket'ta sessizce basarisiz oluyor). COZUM: eslem-ozel.json 'surum' alanini "
            "artirin -> yeni anahtar yazilir; CI girdisini (paket_anahtar) yeni anahtara "
            "cevirin. Bu betik silme YAPMAZ."
            % (anahtar, bekleniyor[:16], gelen[:16]))
    print("yuklendi + GERI OKUNDU: r2://%s/%s (%d bayt, sha256 %s)"
          % (BUCKET, anahtar, os.path.getsize(arsiv), gelen[:16]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", metavar="DIZIN",
                    help="paketi bu dizine topla, YUKLEME (kabul testleri kullanir)")
    ap.add_argument("--uyelik-dir",
                    default=os.environ.get("PRUVO_UYELIK_DIR",
                                           "/Users/okan/dev/pruvo/.uyelik-kodlar"))
    ap.add_argument("--jenerator-dir",
                    default=os.environ.get(
                        "PRUVO_JENERATOR_DIR",
                        os.path.expanduser("~/dev/pruvo-jenerator/jeneratorler")))
    args = ap.parse_args()

    if args.yerel:
        surum = topla(args.yerel, args.uyelik_dir, args.jenerator_dir)
        print("paket toplandi (v%d): %s" % (surum, args.yerel))
        return

    with tempfile.TemporaryDirectory() as tmp:
        paket_dizin = os.path.join(tmp, "paket")
        surum = topla(paket_dizin, args.uyelik_dir, args.jenerator_dir)
        arsiv = os.path.join(tmp, "paket.tar.gz")
        # BELIRLENIMCI ARSIV: ayni icerik -> ayni bayt. mtime/uid/gid sifirlanir ve gzip
        # basligina zaman damgasi YAZILMAZ (mtime=0). Gerekce: yukleme dogrulamasi
        # (yukle_ve_dogrula) R2'deki nesnenin baytini bizim baytimizla karsilastirir;
        # arsiv her kosumda farkli baytlar uretirse "icerik ayni ama bayt farkli" hali
        # SAHTE-KIRMIZI yakardi. Belirlenimci arsivde iddia nettir: R2'deki nesne TAM
        # OLARAK yuklemek istedigimiz icerik mi.
        def _duzle(bilgi):
            bilgi.mtime = 0
            bilgi.uid = bilgi.gid = 0
            bilgi.uname = bilgi.gname = ""
            return bilgi
        with tarfile.open(arsiv, "w:gz", compresslevel=9,
                          format=tarfile.GNU_FORMAT) as tar:
            for ad in sorted(os.listdir(paket_dizin)):
                tar.add(os.path.join(paket_dizin, ad), arcname=ad, filter=_duzle)
        # gzip basligindaki MTIME alanini (bayt 4..7) sifirla: tarfile onu acmaya izin
        # vermez, ama alan bastaki sabit basliktadir ve icerigi etkilemez.
        with open(arsiv, "r+b") as f:
            f.seek(4)
            f.write(b"\x00\x00\x00\x00")
        # Yerel wrangler oturumu (token'siz). shell degiskeni yok — komut listesi.
        # Her yukleme GERI OKUNARAK dogrulanir (bkz. yukle_ve_dogrula docstring'i).
        # SABIT TAKMA ADA YAZILMAZ (bkz. modul docstring'i "SURUMLU ANAHTAR").
        anahtarlar = yuklenecek_anahtarlar(surum)
        for anahtar in anahtarlar:
            yukle_ve_dogrula(anahtar, arsiv, tmp)
        print("")
        print("PAKET SURUMU : v%d" % surum)
        print("R2 ANAHTARI  : %s" % ", ".join(anahtarlar))
        print("CI'YE VERILECEK GIRDI: onizleme-imaj.yml -> paket_anahtar = %s"
              % anahtarlar[0])
        print("  (workflow_dispatch girdisi; sabit 'guncel' takma adi KULLANILMIYOR)")
        # NOT (2026-07-16): ONIZLEME_PAKET_B64 yedegi KALDIRILDI (Okan karari). CI artik
        # paketi dogrudan R2'den ceker: R2_ERISIM_ID/R2_GIZLI_ANAHTAR secret'lari
        # pruvo-ozel'e SALT-OKUMA yetkili 'pruvo-ozel-okuma-ci' token'idir.


if __name__ == "__main__":
    main()
