#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/commit-mesaji-mutasyon.py — commit mesaji sizinti nobetcisinin CURUTME araci.

NE OLCER: "kabul testi YESIL" demek "nobetci CANLI" demek DEGILDIR. Bu arac nobetciyi
BILEREK bozar ve kabul bataryasinin (`--kendini-test`) GERCEKTEN kirmizi yandigini
olcer. Ayrica ILGISIZ bir degisiklik (yorum/bosluk) YESIL kalmalidir — aksi halde
batarya "her seye kirmizi yanan" gurultulu bir alarma donusmus demektir.

🔴 GUVENLIK: mutasyon KOPYAYA uygulanir. Canli dosyalara DOKUNULMAZ; kosum sonunda
   sha256 esitligi ile KANITLANIR (mutant sizarsa arac KIRMIZI yanar).
🔴 CI: 14 Eki 2026'dan beri `nobet.yml` :: `mesaj-nobeti` (SERIT B, yayini
   DURDURMAZ) adimidir. Once "elde kosulan KANIT araci" idi ve tam da bu yuzden 2 ay
   KOR kaldigi fark edilmedi (asagiya bak). Maliyet ~5 dk; kopyalar gecici dizinde.

🔴 KOPYA LISTESI ELLE TUTULMAZ (14 Eki 2026): 9 Agu'da (c09b5d37) kapi
   `git_ortami`'yi KOSULSUZ import etmeye basladi, buradaki elle liste uzamadi ->
   her mutant kopyasi ImportError ile COKTU. Sonuc: K1-K3 "sahte-kirmizi" yandi ve
   DAHA KOTUSU her oldurucu mutant olcum yuzunden degil COKME yuzunden "OLDU"
   sayildi (batarya 2 ay KOR). Onarim: (1) bagimliliklar kapi+kurucunun import ve
   dosya adi dizgelerinden TURETILIR; (2) TABAN — mutasyonsuz kopya once YESIL ve
   SONUC satirina ulasmali, yoksa arac hukum KURMAZ (cikis 3 = OLCULEMEDI, KIRMIZI'dan
   ayri); (3) mutant ancak batarya HUKME ULASIP kirmizi derse OLDU sayilir; cokme OLDU
   DEGILDIR. Ilgisiz kontrol de taban ile AYNI iddia sayisina ulasmalidir.

Kullanim: python3 tools/commit-mesaji-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + her ilgisiz mutant YESIL + canli dosyalar temiz.
Cikis 1 = KIRMIZI (mutant sag kaldi/coktu · ilgisiz kontrol kirmizi · canli dosya degisti).
Cikis 3 = OLCULEMEDI (taban kopyasi hukme ulasamadi; mutant hukmu KURULMADI).
"""
import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "commit-mesaji-kapisi.py")
KUR = os.path.join(TOOLS, "commit-mesaji-hook-kur.py")
OZET = os.path.join(TOOLS, "sizinti-desen-ozetleri.json")
# 🔴 5 Agu 2026 SERIT AYRIMI: `mesaj-nobeti` job'u deploy.yml'den nobet.yml'e TASINDI
# (bloklamayan nobet joblari yayin kosumunun rengini boyamasin diye;
# [[hukum-yanlis-birimde]]). K bolumunun capasi da onunla birlikte tasindi.
YML_ADI = "nobet.yml"
YML = os.path.join(ROOT, ".github", "workflows", YML_ADI)
# Kabul bataryasinin J bolumu katalog markalarini `urunler.json`'dan turetir, K bolumu
# `nobet.yml` adim adlarini okur -> mutant agacinda IKISI DE bulunmalidir, yoksa her
# mutant (ilgisiz kontroller dahil) "olcemedim" yuzunden kirmizi yanar ve arac korlesir.
URUNLER = os.path.join(ROOT, "urunler.json")


SONUC_DESEN = re.compile(r"^SONUC: (\d+)/(\d+) iddia yesil\s*$", re.M)


def turetilmis_bagimliliklar(kokler=(KAPI, KUR)):
    """Kapi + kurucunun `tools/` icindeki yerel bagimliliklari (gecisli, kokler dahil).

    Iki kaynak: (a) `import X` / `from X import` -> `tools/X.py` varsa; (b) govdedeki
    dizge sabiti `tools/` altinda bir DOSYA adiysa (ornek: kendini testin sentetik
    depoya `copy2` ile tasidigi modul, desen ozet dosyasi).
    """
    gorulen = set()
    kuyruk = [os.path.abspath(k) for k in kokler]
    while kuyruk:
        yol = kuyruk.pop()
        if yol in gorulen:
            continue
        gorulen.add(yol)
        if not yol.endswith(".py"):
            continue
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read(), filename=yol)
        adaylar = set()
        for d in ast.walk(agac):
            if isinstance(d, ast.Import):
                adaylar.update(a.name.split(".")[0] + ".py" for a in d.names)
            elif isinstance(d, ast.ImportFrom) and d.module and not d.level:
                adaylar.add(d.module.split(".")[0] + ".py")
            elif isinstance(d, ast.Constant) and isinstance(d.value, str):
                if d.value and "/" not in d.value and len(d.value) < 128:
                    adaylar.add(d.value)
        for ad in adaylar:
            hedef = os.path.join(TOOLS, ad)
            if os.path.isfile(hedef) and hedef not in gorulen:
                kuyruk.append(hedef)
    return sorted(gorulen)


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# (ad, hedef_dosya, eski, yeni, oldurucu_mu)
# "oldurucu" = nobetcinin HUKMUNU ya da KABLOSUNU olduren mutasyon -> batarya KIRMIZI.
MUTANTLAR = (
    ("M1  ad eslesmesi OLDURULDU (ad_isabetleri -> [])", "kapi",
     '    if not kayit:\n        return []\n    uzunluklar =',
     '    if not kayit:\n        return []\n    return []\n    uzunluklar =', True),
    ("M2  alan adi ekseni OLDURULDU (alan_adi_isabetleri -> [])", "kapi",
     '    if not mesaj:\n        return []\n    bulunan = {}',
     '    if not mesaj:\n        return []\n    return []\n    bulunan = {}', True),
    ("M3  normalize OLDURULDU (ham metin doner)", "kapi",
     '    metin = "".join(_ELLE_ESLEM.get(k, k) for k in metin)',
     '    return metin\n    metin = "".join(_ELLE_ESLEM.get(k, k) for k in metin)', True),
    ("M4  sikistirilmis aday akisi KALDIRILDI", "kapi",
     '    jetonlar = bosluklu.split(" ") if bosluklu else []',
     '    return kume\n    jetonlar = bosluklu.split(" ") if bosluklu else []', True),
    ("M5  desen dosyasi yoklugu FAIL-OPEN yapildi", "kapi",
     '    if not os.path.isfile(yol):\n        return None, ("desen ozet dosyasi YOK',
     '    if not os.path.isfile(yol):\n        return {"dongu": 1, "tuz": b"x",'
     ' "desenler": []}, None\n    if False:\n        return None, ("desen ozet dosyasi YOK',
     True),
    ("M6  BOS desen listesi KABUL edildi (fail-open)", "kapi",
     '    if not isinstance(desenler, list) or not desenler:',
     '    if False:', True),
    ("M7  git yorum ayiklama KALDIRILDI (sablon hukme girer)", "kapi",
     '    satirlar = []\n    for satir in (ham or "").splitlines():',
     '    return (ham or "").strip()\n    satirlar = []\n'
     '    for satir in (ham or "").splitlines():', True),
    ("M8  CI maskesi OLDURULDU (host acik yazilir)", "kapi",
     '    ham = (host or "").strip()\n    if not ham:\n        return "*"',
     '    return host\n    ham = (host or "").strip()\n'
     '    if not ham:\n        return "*"', True),
    ("M9  PUBLIC_ALAN hukmu OLDURULDU (_public_mi -> False)", "kapi",
     'def _public_mi(host):\n    host = host.lower().strip(".")',
     'def _public_mi(host):\n    return False\n    host = host.lower().strip(".")', True),
    ("M10 UZANTI elemesi KALDIRILDI (dosya adlari alan adi sayilir)", "kapi",
     '        if son in UZANTI or son not in TLD:', '        if son not in TLD:', True),
    # 🔴 `= 0` DEGIL: kendini testin fikstur kurucusu da ASGARI_DONGU'yu kullanir ve
    # pbkdf2 0 donguyu ValueError ile reddeder -> mutant OLCULMEDEN COKER (14 Eki
    # olculdu). `= 1` gecerli ama ucuz; F4 iddiasi tarafindan oldurulur.
    ("M11 asgari dongu esigi DUSURULDU (ucuz artefakt kabul)", "kapi",
     'ASGARI_DONGU = 5000', 'ASGARI_DONGU = 1', True),
    ("M12 KANCA CAGRI SATIRI SILINDI (blok var, olcum yok)", "kur",
     'if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then\n'
     '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."\n'
     '  exit 1\n'
     'fi\n', 'true\n', True),
    ("M13 KANCA cagrisi YORUMA alindi (nobetci-cagri-satiri-nobetsiz sinifi)", "kur",
     'if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then',
     'if ! echo python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then',
     True),
    ("M14 KANCA `exit 1` -> `exit 0` (fail-open)", "kur",
     '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."\n'
     '  exit 1\n', '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici'
     ' kimligi."\n  exit 0\n', True),
    ("M15 KANCA fail-closed on-kosulu fail-OPEN yapildi (betik yoksa gec)", "kur",
     '  echo "!! Sizinti kapisi fail-closed\'dir. Kasten atlamak icin: '
     'git commit --no-verify"\n  exit 1\n', '  exit 0\n', True),
    # --- SURE EKSENI (donanimdan bagimsiz olcu birimi) ---
    # 🔴 M16 sure ekseninin CEKIRDEGIDIR: cevrim oldurulunce olculen sure yine "ham
    # ms" olur — yani kapi tekrar donanima bagimlidir ve CI'da kalici kirmizi doner.
    # Kalibrasyon makinesinde olcek ~1,0 oldugu icin I1/I2 bunu GOREMEZ (yerelde
    # olculdu: mutant SAG KALIYORDU); yakalayan iddia, cevrimi 3,58x enjekte edilmis
    # degerlerle cagiran I4'tur. Bu yuzden cevrim modul duzeyinde TEK bir fonksiyondur.
    ("M16 sure CEVRIMI OLDURULDU (referans_ms -> ham ms; olcu birimi yalan)",
     "kapi", "    if not birim_ms or birim_ms <= 0:\n        return 0.0\n"
     "    return ham_ms * (referans_birim_ms / birim_ms)",
     "    return ham_ms", True),
    # NOT: "IS TAVANI gevsetildi" (tavan = 10**9) bilerek EKLENMEDI. Olculdu: bir
    # KAPIYI gevseten mutant, o kapinin bekcilik ettigi kosul IHLAL EDILMEDIKCE
    # yakalanamaz -> temiz agacta SAG KALIR ve araci yalanci-kirmiziya bogar.
    # Tavanin yuk tasidigini M18 KANITLAR: kisit gercekten kaybolunca I3 kirmizi yanar.
    ("M18 aday uretimi KELIME BASI kisitini kaybetti (her konumdan aday)", "kapi",
     "    for bas in _kelime_baslari(bosluklu):",
     "    for bas in range(len(bosluklu)):", True),
    # --- ALAN ADI EKSENI: MARKA MUAFIYETI BYPASS'A DONUSMESIN ---
    # 17 Eyl (b922ee3b) ozet ile muafiyet arasina rezerve-TLD kolu girdi; capa onu
    # da kapsar (sira: muafiyet -> ozet -> rezerve = muafiyet ozeti EZER).
    ("M19 marka muafiyeti OZET ONCELIGINI EZDI (muafiyet -> bypass)", "kapi",
     "        no = _host_desen_isabeti(host, kayit)\n"
     "        if no is not None:\n"
     "            isabet.append((host, konum, no))\n"
     "            continue\n"
     "        if rezerve_tld_mi(host):\n"
     "            continue\n"
     "        govde = _kayitli_govde(host)\n"
     "        if govde is not None and govde in markalar:\n"
     "            continue",
     "        govde = _kayitli_govde(host)\n"
     "        if govde is not None and govde in markalar:\n"
     "            continue\n"
     "        no = _host_desen_isabeti(host, kayit)\n"
     "        if no is not None:\n"
     "            isabet.append((host, konum, no))\n"
     "            continue\n"
     "        if rezerve_tld_mi(host):\n"
     "            continue", True),
    ("M20 marka muafiyeti HER host'u yesil yapti (alan adi ekseni fiilen olu)",
     "kapi", "    if markalar is None:\n        markalar = katalog_markalari()",
     "    if markalar is None:\n        markalar = katalog_markalari()\n"
     "    return []", True),
    ("M21 vitrin host teshisi ALAN ADINI YAZAR (nobetci sizinti kaynagi olur)",
     "kapi", '                "eslesen bir host gecti (konum %d). Alan adi BILEREK '
     'yazilmiyor. "\n                "Mesaji duzenle: adres yerine notr ifade '
     "('kaynak platform').\"\n                % (no, konum))",
     '                "eslesen bir host gecti: %s (konum %d)."\n'
     "                % (no, host, konum))", True),
    ("M22 host ozet eslesmesi OLDURULDU (_host_desen_isabeti -> None)", "kapi",
     "    if not kayit:\n        return None\n    etiketler =",
     "    if not kayit:\n        return None\n    return None\n    etiketler =", True),
    # --- BAYAT ADIM ADI NOBETI ---
    # 🔴 BU MUTANT KAPIYI DEGIL IS AKISINI bozar: adim adina yeniden sabit bir iddia
    # SAYISI konur. Nobetci (K1) bunu KIRMIZI yakmali — yoksa "56 iddia / gercek 58"
    # arizasi sessizce geri gelir. Guvenlik iddialarini olduren mutantlarin aksine
    # bunun capasi nobet.yml'dedir (serit ayrimindan sonra), bu yuzden `yml` hedefi var.
    ("M23 adim adina bayat iddia SAYISI geri kondu (nobet.yml)", "yml",
     '- name: "Commit mesaji sizinti nobetcisi: kendini test (gercek git; sayi ciktida)"',
     '- name: "Commit mesaji sizinti nobetcisi: kendini test (56 iddia, gercek git)"',
     True),
    # --- MASKELEME (1 Agu 2026 OLCULEN AKTIF SIZINTI KANALI) ---
    # 🔴 M24 arizanin TA KENDISIDIR: maskeleme yalniz ILK etikete uygulanirsa cok
    # etiketli bir hostta gizli govde (uydurma ornek: `altalan.gizliad.com`) PUBLIC
    # Actions gunlugune ACIK duser. Olculdu: 12 varyantin 9'unda ad acik kaliyordu.
    ("M24 maskeleme ILK ETIKETLE sinirlandi (gizli govde PUBLIC gunluge acik duser)",
     "kapi",
     "    gizlenecek = etiketler[:-1] if tld_acik else etiketler\n"
     '    parcalar = ["".join("*" if k.isalnum() else k for k in e) '
     "for e in gizlenecek]\n"
     "    if tld_acik:\n"
     "        parcalar.append(son)\n"
     '    return ".".join(parcalar)',
     "    govde = etiketler[0]\n"
     '    gizli = (govde[0] + "*" * (len(govde) - 1)) if govde else "*"\n'
     '    return ".".join([gizli] + etiketler[1:])', True),
    # 🔴 M25 arizanin IKINCI yarisi: gizli ad ALT/ORTA etiketse eski akis kumesi onu
    # desen olarak TANIMIYOR -> host "taninmayan alan adi" koluna dusuyor ve KANCA
    # kolunda ACIK yazdiriliyordu (D11 bunu olcer).
    ("M25 host desen akislari ESKI kumeye dondu (alt/orta etiket taninmaz)", "kapi",
     "    akislar = set()\n"
     "    for bas in range(len(etiketler)):\n"
     "        for son_ in range(bas + 1, len(etiketler) + 1):\n"
     "            dilim = etiketler[bas:son_]\n"
     '            akislar.add(" ".join(dilim))\n'
     '            akislar.add("".join(dilim))',
     "    govde = etiketler[0]\n"
     '    akislar = (" ".join(etiketler), "".join(etiketler), govde,\n'
     '               " ".join(etiketler[:-1]), "".join(etiketler[:-1]))', True),
    # --- MUAFIYET EKSENI: KAYITLI GOVDE (1 Agu 2026 OLCULEN KACAK + YANLIS-POZITIF)
    # 🔴 M26 arizanin TA KENDISIDIR: muafiyet ILK etiketten okununca
    # `<marka>.<vitrin>.com` — gercek bayi/pazaryeri URL bicimi — 1294/1294 YESIL
    # yaniyor (kacak tamamen acik) ve `www.`/`shop.` onekli MESRU marka adresleri
    # 1293/1294 KIRMIZI yaniyordu (alarm korlugu -> `--no-verify` aliskanligi).
    ("M26 muafiyet ILK ETIKETE dondu (kacak acilir + yanlis-pozitif geri gelir)",
     "kapi",
     "    govde = etiketler[-2]\n"
     "    if govde in IKINCI_SEVIYE_EK and len(etiketler) >= 3:\n"
     "        govde = etiketler[-3]",
     "    govde = etiketler[0]", True),
    # 🔴 M27 "daha comert olsun" refleksinin bedelini olcer: muafiyet HER etikete
    # bakarsa marka adi host'un HERHANGI bir yerinde gecen TUM adresler yesil olur —
    # yani `<marka>.<vitrin>.com` yeniden kacak verir. Muafiyet TEK bir etiketten,
    # KAYITLI govdeden okunmalidir.
    ("M27 muafiyet HER ETIKETE bakti (any-label -> muafiyet gene bypass olur)",
     "kapi",
     "        govde = _kayitli_govde(host)\n"
     "        if govde is not None and govde in markalar:\n"
     "            continue",
     "        if any(normalize(_e).replace(\" \", \"\") in markalar\n"
     "               for _e in host.lower().strip(\".\").split(\".\")):\n"
     "            continue", True),
    # 🔴 M28 ikinci-seviye ek listesinin YUK TASIDIGINI kanitlar: bosaltilirsa
    # `<marka>.com.tr` / `<marka>.co.uk` govdesi `com`/`co` sanilir ve MESRU marka
    # adresleri yeniden KIRMIZI yanar (yanlis-pozitif geri gelir).
    ("M28 ikinci-seviye ek listesi BOSALTILDI (cok parcali uzantida yanlis-pozitif)",
     "kapi",
     'IKINCI_SEVIYE_EK = frozenset(("com", "co", "net", "org", "gov", "edu", "ac"))',
     "IKINCI_SEVIYE_EK = frozenset()", True),
    # 🔴 M29 M28'IN TERS YONUDUR ve BAGIMSIZ CURUTUCU tarafindan bulundu: liste
    # yalniz "cok kisa" yonunde korunuyordu. Jenerik etiketler listeye EKLENINCE
    # `<marka>.shop.com` govdesi `marka` sanilir ve MUAF olur -> her tedarikci vitrini
    # bir `shop`/`store` alt alaniyla muaflasabilir. Bu mutant ILK yazildiginda
    # batarya 93/93 YESIL geciyordu (OLU NOBETCI); J17 o deligi kapatti.
    ("M29 ikinci-seviye ek listesi SISIRILDI (jenerik etiket -> muafiyet kacagi)",
     "kapi",
     'IKINCI_SEVIYE_EK = frozenset(("com", "co", "net", "org", "gov", "edu", "ac"))',
     'IKINCI_SEVIYE_EK = frozenset(("com", "co", "net", "org", "gov", "edu", "ac",\n'
     '                              "www", "shop", "store", "web"))', True),
    # --- CI MENZILI = origin/main..after (15 Eki 2026) ---
    # M30: ayirt edici kosul (c) silinir -> main itmesinde menzil BOS, yeni gelen
    # bozuk commit HIC taranmaz (V4 yakalar). M31: fallback kaldirilir -> origin/main
    # cozulemeyince tarama bos doner (V3 yakalar). M32: menzil `after^..after`'a
    # daraltilir -> merge'de main tarafi yine yargilanir (V1) / dalin onceki commit'i
    # kacar (V2).
    ("M30 menzil HER ZAMAN origin/main..after (main itmesi BOS kalir)", "kapi",
     "    ata = _git([\"merge-base\", \"--is-ancestor\", sonra, ana], kok=kok)"
     ".returncode\n"
     "    if ata == 0:\n"
     "        return None, \"after zaten %s icinde (main itmesi)\" % ANA_REF\n"
     "    if ata != 1:\n"
     "        return None, \"ata sinamasi rc=%d\" % ata\n", "", True),
    ("M31 before..after FALLBACK'i kaldirildi (origin/main yoksa bos tarama)",
     "kapi",
     "        sebep = \"%s menzili okunamadi: %s\" % (ANA_REF, hata)\n",
     "        sebep = \"%s menzili okunamadi: %s\" % (ANA_REF, hata)\n"
     "    return [], \"%s..yok (%s)\" % (ANA_REF, sebep), None\n", True),
    ("M32 menzil after^..after'a DARALTILDI", "kapi",
     "    return \"%s..%s\" % (ana, sonra), None",
     "    return \"%s^..%s\" % (sonra, sonra), None", True),
    # --- ILGISIZ (kontrol): batarya YESIL kalmali ---
    ("K1  ilgisiz: baslik yorumunda kelime degisti", "kapi",
     "IKI KOL — biri ONLER, digeri GORUNUR KILAR",
     "IKI KOL - biri ONLER, digeri GORUNUR KILAR", False),
    ("K2  ilgisiz: fonksiyon arasina bos satir eklendi", "kapi",
     "\ndef maskele(host):", "\n\ndef maskele(host):", False),
    ("K3  ilgisiz: kurulum betigine yorum satiri eklendi", "kur",
     "def kurulu_mu(yol):", "# ilgisiz yorum\ndef kurulu_mu(yol):", False),
)


def _kos(mutasyon, kopyalar):
    """Bir kopya agacinda kendini testi kosar. mutasyon=None -> TABAN (degismemis).

    Donus: (rc|None, tani, yesil, toplam). rc=None -> mutasyon UYGULANAMADI.
    yesil/toplam None -> batarya SONUC satirina ULASAMADI (cokme/zaman asimi).
    """
    tmp = tempfile.mkdtemp(prefix="pruvo-cm-mut-")
    try:
        t_tools = os.path.join(tmp, "tools")
        os.makedirs(t_tools)
        t_yml = os.path.join(tmp, ".github", "workflows")
        os.makedirs(t_yml)
        for kaynak in kopyalar:
            shutil.copy2(kaynak, os.path.join(t_tools, os.path.basename(kaynak)))
        shutil.copy2(YML, os.path.join(t_yml, YML_ADI))
        # urunler.json 14,4 MB'dir ve HICBIR mutant onu degistirmez -> kopya yerine
        # sembolik bag (23 mutantta ~330 MB gereksiz I/O'dan kacinilir).
        os.symlink(URUNLER, os.path.join(tmp, "urunler.json"))
        if mutasyon is not None:
            hedef, eski, yeni = mutasyon
            yol = {"kapi": os.path.join(t_tools, os.path.basename(KAPI)),
                   "kur": os.path.join(t_tools, os.path.basename(KUR)),
                   "yml": os.path.join(t_yml, YML_ADI)}[hedef]
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                return (None, "CAPA BULUNAMADI (mutasyon uygulanamadi — arac bayat)",
                        None, None)
            if metin.count(eski) != 1:
                return (None, "capa %d kez gecti (tek olmali)" % metin.count(eski),
                        None, None)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
        try:
            p = subprocess.run(
                [sys.executable, os.path.join(t_tools, os.path.basename(KAPI)),
                 "--kendini-test"], capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            return -1, "ZAMAN ASIMI (900 sn)", None, None
        m = SONUC_DESEN.findall(p.stdout)
        yesil, toplam = (int(m[-1][0]), int(m[-1][1])) if m else (None, None)
        kirmizi = [s.strip() for s in p.stdout.splitlines()
                   if s.strip().startswith("❌")]
        if kirmizi:
            tani = "; ".join(kirmizi[:3])
        elif toplam is None:
            son = [s for s in (p.stderr or p.stdout).strip().splitlines() if s.strip()]
            tani = "SONUC satiri yok; son satir: %s" % (son[-1][:160] if son else "-")
        else:
            tani = "(kirmizi iddia yok)"
        return p.returncode, tani, yesil, toplam
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    kopyalar = sorted(set(turetilmis_bagimliliklar()) | {OZET})
    izlenen = sorted(set(kopyalar) | {YML, URUNLER})
    canli_once = {y: _sha(y) for y in izlenen}
    print("kopya kumesi (kaynaktan TURETILDI): %s"
          % ", ".join(os.path.basename(k) for k in kopyalar))

    # TABAN: mutasyonsuz kopya hukme ulasip YESIL demezse hicbir mutant hukmu
    # anlamli degildir (cokme "OLDU" sayilir, kontrol "sahte-kirmizi" yanar).
    t_rc, t_tani, t_yesil, t_toplam = _kos(None, kopyalar)
    if t_rc != 0 or t_toplam is None or t_yesil != t_toplam:
        print("⚪ OLCULEMEDI: TABAN kopyasi temiz DEGIL (rc=%s, SONUC=%s/%s): %s"
              % (t_rc, t_yesil, t_toplam, t_tani))
        print("   Kopya agacinda eksik bagimlilik/cevre var; mutant hukmu KURULMADI.")
        return 3
    print("TABAN: rc=0 · %d/%d iddia yesil (mutasyonsuz kopya)" % (t_yesil, t_toplam))

    sonuclar = []
    for ad, hedef, eski, yeni, oldurucu in MUTANTLAR:
        rc, tani, yesil, toplam = _kos((hedef, eski, yeni), kopyalar)
        sonuclar.append((ad, oldurucu, rc, tani, yesil, toplam))

    hatalar = []
    print("MUTANT                                                        BEKLENEN  RC  HUKUM")
    print("-" * 100)
    for ad, oldurucu, rc, tani, yesil, toplam in sonuclar:
        beklenen = "KIRMIZI" if oldurucu else "YESIL"
        if rc is None:
            hukum = "OLCULEMEDI"
            hatalar.append("%s -> %s" % (ad, tani))
        elif toplam is None:
            # Batarya SONUC satirina ulasmadi: cokme bir OLCUM degildir (taban
            # temizdi, yani bu mutant kopyayi calisamaz hale getirdi).
            hukum = "COKTU ❌"
            hatalar.append("%s COKTU (hukme ulasilmadi; cokme OLDU sayilmaz): %s"
                           % (ad, tani))
        elif oldurucu:
            hukum = "OLDU ✅" if rc != 0 else "SAG KALDI ❌"
            if rc == 0:
                hatalar.append("%s SAG KALDI (batarya bu mutasyonu GORMUYOR)" % ad)
        else:
            temiz = rc == 0 and yesil == toplam == t_toplam
            hukum = "YESIL ✅" if temiz else "SAHTE-KIRMIZI ❌"
            if not temiz:
                hatalar.append("%s ilgisiz degisiklikte KIRMIZI yandi (SONUC %s/%s, "
                               "taban %d): %s" % (ad, yesil, toplam, t_toplam, tani))
        print("%-60s  %-8s  %-3s %s" % (ad[:60], beklenen,
                                        "-" if rc is None else rc, hukum))
    canli_sonra = {y: _sha(y) for y in izlenen}
    for yol in canli_once:
        if canli_once[yol] != canli_sonra[yol]:
            hatalar.append("🔴 CANLI DOSYA DEGISTI (mutant sizdi): %s" % yol)
    print("-" * 100)
    print("canli dosya sha256 esitligi: %s"
          % ("TAM ✅" if canli_once == canli_sonra else "BOZUK ❌"))
    for yol, ozet in sorted(canli_once.items()):
        print("   %-44s %s" % (os.path.basename(yol), ozet[:16]))
    oldu = sum(1 for _a, o, rc, _t, _y, top in sonuclar
               if o and rc not in (None, 0) and top is not None)
    oldurucu_sayi = sum(1 for s in sonuclar if s[1])
    yesil_k = sum(1 for _a, o, rc, _t, y, top in sonuclar
                  if not o and rc == 0 and y == top == t_toplam)
    kontrol_sayi = sum(1 for s in sonuclar if not s[1])
    print("SONUC: oldurucu mutant %d/%d OLDU · ilgisiz kontrol %d/%d YESIL"
          % (oldu, oldurucu_sayi, yesil_k, kontrol_sayi))
    if hatalar:
        print("\nKIRMIZI:")
        for h in hatalar:
            print("  * " + h)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
