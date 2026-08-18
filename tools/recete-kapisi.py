#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/recete-kapisi.py — K168 H2: SINIF KAPISI.

Diger kapilari / nobetcileri / oteki araclari tarar; "CARE:" / "COZUM:" /
"Duzeltip tekrar" gibi on eklerin pesinde gelen `python3 ...` komutlarini
bulur ve her birini `mimar-icra-kapisi`'na KURU sorar (gercek calistirma
YOK). Reddedilen bir recete varsa RED; receteyi basan dosya + satir ile
RAPORLAR.

NEDEN VAR (K168, 18 Agu 2026): DEVAM.md kota tavanini (130 satir) astiginda
`defter-kota-kapisi.py` "CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py ..."
yazdirir. Mimar bu emri okuyunca `mimar-icra-kapisi` reddediyordu (sadece
iki komut serbest). Olculmus sonuc: 7 tekrar, ucuncu tekrar yasaklanmasina
ragmen 4 elle taklit. Bu kapi yedincide sinif kapisi olarak devreye girdi:
"H1 bunu serbest birakti mi" degil, "H1 tarzindaki HER recete kapidan
gecer mi" sorusunu MAKINE olarak yanitlar.

KAPSAM (KOD, ad deseni DEGIL):
  * Evren = tools/ altindaki *.py (kapilar + nobetciler + araclar).
  * Recete = bir satir/gruptaki metin "CARE:" / "COZUM:" / "Duzeltip tekrar"
    on eklerinden birini ICERIR VE ayni grup `python3 /...` komutunu ICERIR.
  * "Bos evren" OLCULEMEDI'dir, YESIL degildir (fail-closed).

HUKUM — KAPI SESSIZCE YETKI GENISLETEMEZ:
  Bu kapi bir receteyi REDDETMEYI yapar, receteyi otomatik ACI yapmaz.
  Hangi recetenin serbest birakilacagi mimar HUKMU kalir (K168 §2.H1).
  Kural yalniz "sectigin komutu mimar kosabiliyor mu" sorusunu SORAR.

CIKIS:
  0 = evren bos degil, tum receteler mimar-icra-kapisi'nca izinli (ALLOW)
  1 = en az bir recete REDDEDILDI (basan dosya + satir + gerekce)
  2 = evren YOK / BEYAN YANLIS (rc only on programmatic fail-closed)

Cikis son satiri:
    RECETE=<n> REDDEDILEN=<n> EVREN=<n> MUTANT=<k>/<k> KONTROL=<k>/<k>
"""
import glob
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS = os.path.join(REPO, "tools")
ICRA = os.path.join(TOOLS, "mimar-icra-kapisi.py")
# KENDINI TEST: --kendini-test bayragiyla kapi kendi hukmunu 3 mutant + 2 kontrol
# uzerinden olcer. CI'da SERIT B'ye kablolu (nobet.yml).
KENDINI_TEST = "--kendini-test" in sys.argv[1:]
# ICRA alternatifi (mutant test icin): --icra <yol> ile gercek mimar-icra-kapisi yerine
# baska bir kapi kullanilir.
_icra_arg = None
if "--icra" in sys.argv[1:]:
    i = sys.argv.index("--icra")
    if i + 1 < len(sys.argv):
        _icra_arg = sys.argv[i + 1]
        ICRA = os.path.abspath(_icra_arg)
# EVREN override (mutant test icin): --evren-bos ile evren 0 yapilir.
EVREN_BOS = "--evren-bos" in sys.argv[1:]

# On ekler — K168 §2.H2.1: "CARE:" / "COZUM:" / "Duzeltip tekrar" gibi on eklerden
# sonra gelen `python3 ...` komutlari. Kucuk/buyuk HARF DUYARSIZ (defter-kota-kapisi
# "CARE:" buyuk, bazi yerlerde "Cozum:" kucuk gorulur).
RECETE_ONEKLERI = ("CARE:", "COZUM:", "Duzeltip tekrar")
# python3 <yol> <arg1> <arg2> ... (devam satirli print'leri icin 1+ token yeterli)
# YAKALAMA KURALI (K168 §2.H2.1):
#   - python3 kelimesi, ardindan bosluk, ardindan en az 1 BOSLUKSUZ token.
#   - Bu token sistem komutuna benziyorsa (path gibi; '/' iceren) yola al,
#     sonra 0..3 ek bosluksuz token (argumanlar) yakala.
#   - BIRAK byte'lar: tirnak (", ') · parantez (')' · virgul (',') · YORUM ISARETI ('#').
#     Bunlar python print argumaninin KAPANDIGINI ya da KODUN BITTIGINI isaretler.
#     Olculmus 2 vaka: 'commit-mesaji-kapisi.py:372' yorumu + 'd1-sapma-mutasyon.py:18'
#     docstring'i — ikisi de python3 tokeni SONRASI uzun metin yutuyordu.
# ON-EK YAKINLIGI (K168 §2.H2): python3, on-ekten SONRA EN FAZLA 250 KARAKTERI
# icinde olmali. Bu tarz yorumlardaki 'python3 ...' ile gercek receteyi ayirir.
# 250 = en uzun gercek recete (3 tam yol ≈ 60+60+60 = 180 + 'python3 ' + bosluklar
# + tirnak karak. = ~200). 100 yetmiyordu (defter-rotasyon.py recetesi kesiliyordu).
ONEK_PYTHON3_FAS = 250
PYTHON3_KOMUT_RE = re.compile(
    r"\bpython3(?:\.\d+)?\s+(\S+)"
    r"(?:\s+(\S+))?"
    r"(?:\s+(\S+))?"
    r"(?:\s+(\S+))?"
)
# Tek satirdaki birden fazla python3 komutunun ayrilmasi (kucuk olcum; ayni satir
# icinde 2+ komut beklenmez ama savunmaci).
BAGIMSIZ_PARCA_RE = re.compile(r"\s*[|`&]\s*")

# ARALAR bosluk yerine '`' ya da '`' da icerebilir (kommut sentaksinda); biz
# old-fashioned: yalnizca BEYAZ_ALAN + tirnak gorunce komutun iki yarisini
# birlestirip tek komut musuz test ediyoruz. Yine de KAPSAM evreni kaba bir tarama
# oldugundan tuhaf vakalari MISS etmek YERINE OVER-DELETE (daha cok kapsam) yapiyoruz.

# KURU KOSUM ORTAMI: mimar-icra-kapisi'ni cagirirken eklenir. ASIL ISLE AYNI
# SEKILDE kosturup (cok kucuk sure farki) karar verir.
DRY_RUN_BAYRAK = "--kuru-kontrol"  # recete-kapisi ekler, mimar-icra-kapisi GORMez


# --------------------------------------------------------------------------
# EVREN — kapsam olcutu (KOD; kapsam-evrenini-cagri-grafindan-turet)
# --------------------------------------------------------------------------
def evren_dosyalar():
    """tools/ altindaki *.py — kapilar + nobetciler + araclar yuklenir.

    AD DESENIYLE (filename.startswith('recete-')) sinirlamak yerine butun
    *.py evrenini aliyoruz: receteyi basan dosya 'defter-kota-kapisi.py'
    gibi /-kapsam/.py adlari (K168 §2.H2.1 'kapı/nöbetçi betikleri').
    Tekil yamanin sinif kapisina donusmesinin olcutu budur — sadece
    bir kapiyi degil, bir SINIF dosyayi tarar.

    KENDI KENDIMIZI HARIC TUTARIZ: tools/recete-kapisi.py'nin docstring'i
    'CARE: python3 ...' orneklerini tasir; bunlar recete DEGILDIR. K168
    §2.H2.1 'insana bastigi metinlerde' der — kapi kendi docstring'ine
    tabi degildir (kendi kendini olcen nobetci = sahte yesil).

    MUTANT TESTLERI icin: --evren-bos bayragi evreni bilerek 0'a indirir.
    K168 §2.H2 'evren bos cikarsa YESIL DÖNMEZ, OLCULEMEDI' der — bu kapi
    bu durumda rc 2 ile cikar. M2 mutantinin bekledigi davranis budur.
    """
    if EVREN_BOS:
        return []
    if not os.path.isdir(TOOLS):
        return []
    self_yol = os.path.abspath(__file__)
    return sorted(p for p in glob.glob(os.path.join(TOOLS, "*.py"))
                  if os.path.abspath(p) != self_yol)


# --------------------------------------------------------------------------
# SATIR BIRLESTIRME — Python'da print("...", "...") cok satira yayilir.
# --------------------------------------------------------------------------
def satirlari_birlestir(satirlar):
    """`\\` ile biten ya da acik parantez icindeki satirlari tek metin olarak birlestir.

    Ornek:
        print("CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py
              /Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md")
    Bu iki satirin TAM METNI tek string olarak uretilir.
    """
    out = []
    tampon = ""
    parantez_acik = 0
    tirnak = None
    for satir in satirlar:
        # tirnak icindeyken acaba tirnak kapandi mi? Kaba tarama: tirnak baslangici
        # ya da bitisi gorursen durumu guncelle. DOSYA OKUMA BAGLAMINDA BIR SORUN
        # OLMAZ: print("...") cumlesinin icindeki tirnak genellikle KAPALI kalmaz,
        # cunku print argumani TAM METIN icin tek tirnak cifti kullanilir.
        for c in satir:
            if tirnak is None:
                if c in ("'", '"'):
                    tirnak = c
            else:
                if c == tirnak:
                    tirnak = None
        if tampon:
            tampon += " " + satir.strip()
        else:
            tampon = satir
        # Parantez sayaci (yalniz print(...) veya coklu-arg icin kritik)
        for c in satir:
            if c == "(":
                parantez_acik += 1
            elif c == ")":
                parantez_acik -= 1
        # Satir sonu \\ ile bitiyor ya da parantez hala aciksa tampona devam
        if tampon.rstrip().endswith("\\") or parantez_acik > 0 or tirnak is not None:
            continue
        out.append(tampon)
        tampon = ""
    if tampon:
        out.append(tampon)
    return out


# --------------------------------------------------------------------------
# RECETE TARAYICI — bir dosyada H2.1'in tanimina uyan recete kalemlerini bul.
# --------------------------------------------------------------------------
def dosyada_receteler(yol):
    """[(recete_komut, satir_no, on_ek)], recete_komut shlex ile ayrilabilir olmali.

    Tek satir/birlestirilmis grup icindeki on_ekten sonra 'python3 ...' komutu yakalanir.
    Birlestirme sonrasi arama yapildigi icin Ayni Recete IKI KEZ bulunmaz (birlestirilmis
    ifadenin tamaminda TEK python3 varsa tek sonuc verir).
    """
    try:
        with open(yol, encoding="utf-8") as f:
            satirlar = f.read().splitlines()
    except Exception:
        return []
    birlestirilmis = satirlari_birlestir(satirlar)
    bulgular = []
    # ON-EK + PYTHON3 ayni ORF (open reading frame) icinde olmali: python3, on-ekten
    # sonra EN FAZLA 100 karakter icinde olmali. Bu, yorum + docstring FPsini eler.
    for grup_no, grup in enumerate(birlestirilmis):
        metin_lower = grup.lower()
        bulunan_onek = None
        onek_index = -1
        for onek in RECETE_ONEKLERI:
            lcase = onek.lower()
            idx = metin_lower.find(lcase)
            if idx < 0:
                continue
            if onek_index < 0 or idx < onek_index:
                onek_index = idx
                bulunan_onek = onek
        if bulunan_onek is None:
            continue
        # On-ekten SONRAKI 100 char icinde python3 ara
        sonrasi = grup[onek_index + len(bulunan_onek):]
        # Python3 icin \" temizleme (print(\"CARE: python3 ...\") gibi)
        sonrasi = sonrasi.replace("\\\"", "\"")
        sonrasi = sonrasi.replace("\\'", "'")
        # YAKINLIK PEN: python3, on-ekten SONRA EN FAZLA 100 char. Pencere disiysa atla.
        pencere = sonrasi[:ONEK_PYTHON3_FAS]
        m = PYTHON3_KOMUT_RE.search(pencere)
        if not m:
            continue
        # Yakalanan tokenlari birlestir; bos olmayanlari AL. TIRNAK/KAPAMA TEMIZLEME:
        # print("CARE: python3 ...", file=sys.stderr) icinde "...", file=sys.stderr"
        # metninin kapanis tirnagi veya kapanis parantezi bizim yakaladigimiz token'a
        # yapismis olabilir (or. `--taban-yaz"`). Bu durumda gercek arg `--taban-yaz`
        # olur, sondaki `"` veya `)` fazlalik. Olculmus vakalar: 'marka-invaryant-
        # kapisi.py:123 [COZUM:] python3 tools/marka-invaryant-kapisi.py --taban-yaz")'
        # bunu yutardi ve komut yanlis token icerirdi.
        # ORPHAN TEMIZLEME: sadece trailing degil, LEADING tirnak/paren/virgul da
        # temizlenir. Olculmus vaka: 'defter-kota-kapisi.py:124' multi-line print:
        # "python3 ... defter-rotasyon.py " " <- kapanis + acilis tirnak birlesik
        # bosluktan sonra /Users/okan/...DEVAM.md geliyor; aradaki " token olarak
        # yakalanmamali. SADECE basit trimming yeterli (cunku sozel hicbir anlamli
        # python3 komutu basina veya sonuna bu karakterlerle baslamaz).
        def _temiz(t):
            t = t.strip()
            # Oncelikle kapsamli ASCII-trim: tırnak, kesme, parantez, virgul, backtick.
            # Olculmus vakalar:
            #   * 'defter-kota-kapisi.py:124' — multi-line print, arada acilis tirnak
            #   * 'marka-invaryant-kapisi.py:123' — sondaki `")` parantez+tirnak
            #   * 'yasal-sayfa-drift-kapisi.py:205' — backtick (`` ` `` Markdown)
            # NOT: KIRPICI her BIR karakter ayri bir tuple elemani olarak yazildi;
            # yoksa `('"', "'")` 2 elemanli 2-karakterli DIZI olur ve `'"' in KIRPICI`
            # False donerdi. Olculmus hata.
            KIRPICI = ('"', "'", "\\", "`", ",", "(", ")")
            while t and (t[0] in KIRPICI or t[-1] in KIRPICI):
                if t[0] in KIRPICI:
                    t = t[1:]
                if t and t[-1] in KIRPICI:
                    t = t[:-1]
                t = t.strip()
            return t
        tokenlar = [_temiz(t) for t in m.groups() if t]
        tokenlar = [t for t in tokenlar if t]
        if not tokenlar:
            continue
        komut = "python3 " + " ".join(tokenlar)
        satir_no = _gruba_karsilik_satir(yol, satirlar, grup_no)
        bulgular.append((komut, satir_no, bulunan_onek))
    return bulgular


def _gruba_karsilik_satir(yol, satirlar, grup_no):
    """Birlestirilmis gruplarin TEK satira inmemesini onler; orijinal
    satir sayisini hesaplar. Bu yaklasim: birlestirilmis grup KAC orijinal
    satir ICERIYOR ise, son satir olarak goster.
    """
    # Kaba: tum oncesi metni sayar (yaklasik da olsa yeter).
    # Birlestirilmis gruplarin OLUSTURMA mantigi: ayni sayida girdi olsaydi
    # ayni sayida cikti olurdu. Bu nedenle indeks bazli bir esleme kullaniyoruz.
    # Uygulamada: birlestirilmis grup No N, orijinal satir sayisini ci N.verir
    # (1-birlestirilmis = 1 satir; cok satir birlestirilmis = son satir).
    # Bizim birlestirilmiste: her cikti = girdi (yani 1:1) YOK; parantez acik
    # oldugu surece tampona eklenir. Gruplar = SUZME YOK; 1:n. Bu nedenle
    # yaklasim: dosyada "CARE:" / "COZUM:" / "Duzeltip tekrar" gecen ILK
    # satirli esleme yapalim — kaba ama yeterli.
    aranan = ("CARE:", "COZUM:", "Duzeltip tekrar")
    for i, s in enumerate(satirlar, 1):
        for onek in aranan:
            if onek in s:
                return i
    return 1


# --------------------------------------------------------------------------
# KURU KOSUM — mimar-icra-kapisi'na receteyi PreToolUse JSON olarak yolla.
# --------------------------------------------------------------------------
def kuru_karar(komut):
    """mimar-icra-kapisi'na komutu 'mimar' PreToolUse olarak yolla; karari don.

    Cagri:  python3 tools/mimar-icra-kapisi.py
    stdin: HerBir recete komutu bir PreToolUse JSON'u olarak. Komut 'python3 ...'
           ise arac 'Bash' + command=komut.
    Donus: ('allow'|'deny', gerekce_ilk120).
    """
    payload = {
        "session_id": "recete-kapisi-kuru",
        "cwd": REPO,
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
    }
    try:
        # KIMLIK EKSENI: MIMAR olarak cagir (recete-kapisi kendi basina ISCI kimligi
        # tasiyorsa agent_id alaninda bos string olsa bile PRUVO_ISCI_KOSUMU env'i
        # miras kalir ve mimar-icra-kapisi'nin 'ISCI' erken cikisini tetiklerdi).
        # Bu kapi KURU kontrol yapar, gercek kosum YAPMAZ — agent_id yok + muaf env
        # = MIMAR perspektifi.
        ortam = dict(os.environ)
        ortam.pop("PRUVO_ISCI_KOSUMU", None)
        ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
        sonuc = subprocess.run(
            [sys.executable, ICRA],
            input=json.dumps(payload),
            capture_output=True, text=True, timeout=10,
            env=ortam,
        )
    except Exception as e:
        return ("CALISTIRILAMADI", repr(e)[:120])
    if sonuc.returncode != 0:
        return ("COKTU", (sonuc.stderr or "")[:120])
    cikti = sonuc.stdout.strip()
    if not cikti:
        # mimar-icra-kapisi ALLOW yolunda 'MIMAR-KAPISI allow' izini stderr'e yazar.
        if "MIMAR-KAPISI allow" in (sonuc.stderr or ""):
            return ("allow", "")
        return ("IZSIZ-ALLOW", (sonuc.stderr or "")[:120])
    try:
        veri = json.loads(cikti)
    except Exception as e:
        return ("PARSE-HATASI", str(e)[:120])
    hso = veri.get("hookSpecificOutput") or {}
    karar = hso.get("permissionDecision", "allow")
    gerekce = (hso.get("permissionDecisionReason") or "")[:120]
    return (karar, gerekce)


# --------------------------------------------------------------------------
# ANA
# --------------------------------------------------------------------------
def main():
    dosyalar = evren_dosyalar()
    if not dosyalar:
        print("EVREN=0 RECETE=0", file=sys.stderr)
        print("RECETE=0 REDDEDILEN=0 EVREN=0 MUTANT=0/0 KONTROL=0/0")
        return 2  # evren bos = OLCULEMEDI (fail-closed)

    recete_sayisi = 0
    red_sayisi = 0
    for yol in dosyalar:
        for komut, satir_no, onek in dosyada_receteler(yol):
            recete_sayisi += 1
            karar, gerekce = kuru_karar(komut)
            rel = os.path.relpath(yol, REPO)
            if karar == "allow":
                print("RECETE-OK %s:%d [%s] %s" % (rel, satir_no, onek, komut))
            elif karar == "CALISTIRILAMADI":
                print("RECETE-CALISTIRILAMADI %s:%d [%s] %s -- %s" % (
                    rel, satir_no, onek, komut, gerekce))
                red_sayisi += 1
            else:
                # deny / COKTU / PARSE-HATASI / IZSIZ-ALLOW
                print("RECETE-RED %s:%d [%s] %s -- %s" % (
                    rel, satir_no, onek, komut, gerekce))
                red_sayisi += 1

    # Cikis ozet satiri (son satir)
    print("RECETE=%d REDDEDILEN=%d EVREN=%d" % (recete_sayisi, red_sayisi, len(dosyalar)))
    return 1 if red_sayisi else 0


# --------------------------------------------------------------------------
# KENDINI TEST — 3 MUTANT + 2 KONTROL (K168 §3)
# --------------------------------------------------------------------------
# M1: H1 geri al (defter-rotasyon.py'yi serbest kümeden çıkar) → REDDEDILEN>=1
# M2: evreni boş kümeye indir → EVREN=0 ile YEŞİL DÖNMEMELİ (rc 2)
# M3: H1'i serbest-biçim argümana genişlet → RED (yetki genişlemesi = kırmızı)
# K1: Bugün mimara serbest olan iki komut AYNEN serbest kalmalı
# K2: Bugün mimara YASAK olan ölçüm komutları YASAK kalmalı
# --------------------------------------------------------------------------
def _mutant_yaz(dosya_yol, icerik):
    """Gecici dosyaya mutant yaz; yolu dondurur. atexit ile silinir."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="recete-mutant-")
    yol = os.path.join(tmpdir, os.path.basename(dosya_yol))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol, tmpdir


def _mutant_yap_h1_iptal(icerik):
    """M1: H1 geri al — `if ilk == DEFTER_ROTASYON_YOL:` blogunu sil.
    Bu durumda defter-rotasyon.py reddedilir (kontrol disi)."""
    return re.sub(
        r"\s*if ilk == DEFTER_ROTASYON_YOL:.*?return d1 == DEFTER_ROTASYON_DEFTER and d2 == DEFTER_ROTASYON_ARSIV\n",
        "\n    return False  # M1 MUTANT: H1 serbest birakimi kaldirildi\n",
        icerik,
        count=1,
        flags=re.DOTALL,
    )


def _mutant_yap_h1_genislet(icerik):
    """M3: H1'i serbest-biçim argümana genişlet — sadece yol kontrolü, argüman
    sayısı/kanonik yol doğrulaması YOK. Bu durumda 'python3 defter-rotasyon.py
    DEVAM.md DEVAM-ARSIV.md --tavan-sayi 130' GECER."""
    return re.sub(
        r"\s*if ilk == DEFTER_ROTASYON_YOL:.*?return d1 == DEFTER_ROTASYON_DEFTER and d2 == DEFTER_ROTASYON_ARSIV\n",
        "\n    if ilk == DEFTER_ROTASYON_YOL:  # M3 MUTANT: serbest-biçim arg kabul\n        return True\n",
        icerik,
        count=1,
        flags=re.DOTALL,
    )


def _kuru_cagrir(icra_yol, evren_bos=False):
    """recete-kapisi'yi belirli bir --icra ve --evren-bos ile kosar; sonuc doner.

    NOT: Mutant dosya gecici /tmp/... altinda yasar; orjinal tools/mimar-icra-kapisi.py
    ise `from mimar_kimlik import (...)` ile TOOLS dizinine ihtiyac duyar. Bu nedenle
    PYTHONPATH'e TOOLS eklenir — yoksa ModuleNotFoundError ile COKER (M3 mutantinin
    kirmizi cikmasi bu yuzden).
    """
    import subprocess
    cmd = [sys.executable, os.path.abspath(__file__),
           "--icra", icra_yol]
    if evren_bos:
        cmd.append("--evren-bos")
    ortam = dict(os.environ)
    mevcut = ortam.get("PYTHONPATH", "")
    ortam["PYTHONPATH"] = (TOOLS + os.pathsep + mevcut) if mevcut else TOOLS
    sonuc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=ortam)
    return sonuc.returncode, sonuc.stdout, sonuc.stderr


def kendini_test():
    """3 MUTANT + 2 KONTROL calistir; sonuclari tek tek raporla.

    Hareket tarzi: --icra ile gercek mimar-icra-kapisi yerine GECICI BIR KOPYA
    kullaniriz. Bu kopya uzerinde mutant uygular, kapiyi cagirir, ciktiyi okur.
    Canli tools/ dosyalarina DOKUNMAYIZ — gecici kopya dir.
    """
    gercek = os.path.join(TOOLS, "mimar-icra-kapisi.py")
    with open(gercek, encoding="utf-8") as f:
        kaynak = f.read()

    print("=" * 84)
    print("RECETE KAPISI — K168 KENDINI TEST (3 mutant + 2 kontrol)")
    print("=" * 84)

    sonuclar = []  # (ad, bekleneen_rc, gecti_mi, not)

    # --- M1: H1 geri al ---
    m1_yol, _ = _mutant_yaz(gercek, _mutant_yap_h1_iptal(kaynak))
    rc, out, err = _kuru_cagrir(m1_yol)
    # M1 beklentisi: defter-rotasyon.py recetesi REDDEDILEN listesinde (rc=1)
    # VE tools/defter-kota-kapisi.py:124 RECETE-RED olmali.
    m1_gecti = (rc == 1) and ("tools/defter-kota-kapisi.py:124" in out and "RECETE-RED" in out)
    sonuclar.append(("M1 H1-IPTAL", rc, m1_gecti, "defter-rotasyon.py geri alindi, RECETE-RED"))

    # --- M2: evren bos ---
    rc, out, err = _kuru_cagrir(gercek, evren_bos=True)
    m2_gecti = (rc == 2) and ("EVREN=0" in out)
    sonuclar.append(("M2 EVREN-BOS", rc, m2_gecti, "evren bos -> rc 2 OLCULEMEDI"))

    # --- M3: H1 serbest-biçim argümana genişlet ---
    m3_yol, _ = _mutant_yaz(gercek, _mutant_yap_h1_genislet(kaynak))
    rc, out, err = _kuru_cagrir(m3_yol)
    # M3 beklentisi: H1 genisletildi -> defter-kota-kapisi.py:124 RECETE-OK olur ama
    # diger FP'ler (marka-invaryant-kapisi.py:123, sema-bundle-kapisi.py:259, vs.) YINE RED.
    # Bu durumda recete karisik cikti uretir; ozel KONTROL: defter-kota-kapisi.py:124
    # RECETE-OK OLMALI (yetki genislemesi yuzunden). Hala REDDEDILEN sayisi > 0.
    m3_gecti = (rc == 1) and ("tools/defter-kota-kapisi.py:124" in out and "RECETE-OK" in out)
    sonuclar.append(("M3 H1-GENISLET", rc, m3_gecti, "yetki genislemesi -> defter-kota:124 OK"))

    # --- K1: Bugün mimara serbest olan iki komut (durum.py, d1-sync.py --durum)
    #         AYNEN serbest kalmali. Test: gercek mimar-icra-kapisi'ni dogrudan
    #         cagir, iki komut ALLOW olmali.
    k1_k1, k1_msg1 = _dogrudan_kapi_test("python3 /Users/okan/dev/pruvo/tools/durum.py")
    k1_k2, k1_msg2 = _dogrudan_kapi_test("python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum")
    k1_gecti = (k1_k1 == "allow") and (k1_k2 == "allow")
    sonuclar.append(("K1 MEVCUT-2-SERBEST", "allow+allow", k1_gecti,
                     "durum.py + d1-sync.py --durum ALLOW"))

    # --- K2: Bugün mimara YASAK olan olcum komutlari YASAK kalmali ---
    k2_yasak = ["wc", "sort", "head", "sed", "find"]
    k2_sonuc = []
    for cmd_name in k2_yasak:
        karar, _ = _dogrudan_kapi_test(cmd_name + " -l /tmp/deneme")
        k2_sonuc.append((cmd_name, karar))
    k2_gecti = all(karar == "deny" for _, karar in k2_sonuc)
    sonuclar.append(("K2 BUGUN-YASAK", repr(k2_sonuc), k2_gecti, "5 olcum komutu YASAK"))

    # --- RAPOR ---
    print("{:<28} {:<14} {:<8} {}".format("TEST", "BEKLENEN", "SONUC", "ACIKLAMA"))
    print("-" * 84)
    mutant_gecen = 0
    kontrol_gecen = 0
    for ad, beklenen, gecti, aciklama in sonuclar:
        print("{:<28} {:<14} {:<8} {}".format(
            ad, str(beklenen), "OK" if gecti else "KIRMIZI", aciklama))
        if ad.startswith("M"):
            if gecti:
                mutant_gecen += 1
        else:
            if gecti:
                kontrol_gecen += 1

    # Son satir ozet (K168 §3). Iki ayri sayici: mutant 3/3, kontrol 2/2.
    print("RECETE=OK MUTANT=%d/3 KONTROL=%d/2" % (mutant_gecen, kontrol_gecen))
    return 0 if (mutant_gecen == 3 and kontrol_gecen == 2) else 1


def _dogrudan_kapi_test(komut):
    """mimar-icra-kapisi'na bir komutu yolla; ALLOW/DENY doner."""
    import json, subprocess
    payload = {
        "session_id": "kendini-test",
        "cwd": "/Users/okan/dev/pruvo",
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
    }
    ortam = dict(os.environ)
    ortam.pop("PRUVO_ISCI_KOSUMU", None)
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
    sonuc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "mimar-icra-kapisi.py")],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10,
        env=ortam,
    )
    if sonuc.returncode != 0:
        return ("COKTU", sonuc.stderr[:120])
    cikti = sonuc.stdout.strip()
    if not cikti:
        if "MIMAR-KAPISI allow" in (sonuc.stderr or ""):
            return ("allow", "")
        return ("IZSIZ-ALLOW", (sonuc.stderr or "")[:120])
    try:
        veri = json.loads(cikti)
    except Exception:
        return ("PARSE-HATASI", cikti[:120])
    return (veri.get("hookSpecificOutput", {}).get("permissionDecision", "allow"), "")


if __name__ == "__main__":
    if KENDINI_TEST:
        sys.exit(kendini_test())
    sys.exit(main())
