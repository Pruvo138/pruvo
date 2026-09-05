#!/usr/bin/env python3
"""K304 — MIMAR ICRA KAPISININ TEK KAYNAKTAN DAGITIMI (dagitim + bayatlik duzlemi).

OLCULEN ARIZA (27 Agu 2026, KraL-KapiTekKaynak-27Agu; taban raporda):
`mimar-icra-kapisi.py` ALTI evde ALTI AYRI sha256 ile duruyordu — 1498 / 1320 / 965 /
965 / 965 / 801 satir. K318 ROL onarimi yalnizca KraL'da yasadi; `pruvo-hasat`taki kopya
26 Agu'da DONMUSTU ve cip oturumlarini "agent_id bos / ROL eslesmedi" diye REDDEDIYORDU.
Iki mimar birbirini kilitledi.

KOK NEDEN — OLCULDU, TAHMIN DEGIL:
  * kardes evlerdeki dosya bir KOPYA degil, bir TUREV: `tools/mimar-kapi-kur.py` yalnizca
    marker'li KURAL BLOKLARINI (emekli motor / AGENT / MCP / ISCI) enjekte eder, TABANI hic
    yenilemez. Kanonik dosyada bu marker'larin HICBIRI yoktur (KraL 'kaynak' modunda,
    kural govdede yasar) — yani kurulu kopya kaynaktan BYTE olarak asla turemez.
  * bu yuzden "bayatlik = sha esitligi" olcumu bu modelde YAPILAMAZ; bloklu enjeksiyon
    modeli bayatligi OLCULEMEZ kilar. Blok damgalari (EMEKLI_MOTOR_KURAL_SURUMU vb.) yalnizca
    KENDI bloklarini olcer, GOVDEYI olcmez — K318 tam da govdedeydi.
  * kanonik govde ev-bagimsiz DEGIL: iki sabit (REPO_ONEKI, GIT_WORKTREE_KAYIT) eve
    gomulu, ve `mimar_kimlik` modulu yalnizca KraL'in tools/ dizininde.

COZUM SINIFI (K304 — "bayat tek kaynak"): KOPYAYI KALDIR, GOVDEYI TEK BIRAK.
Kardes evdeki dosya artik bir govde degil, bir SHIM'dir: kanonik dosyayi CALISMA ANINDA
okur, iki ev sabitini kendi evine cevirir ve exec eder. Boylece:
  * kaynakta yapilan HER degisiklik bes evde ANINDA canlidir (dagitim adimi YOK),
  * "kurulu kopya kaynaktan geride" hali YAPISAL OLARAK IMKANSIZDIR,
  * geriye kalan tek bayatlik ekseni SHIM'in KENDISIDIR — o da kaynaktan BAGIMSIZ
    (govde degisince shim degismez), kisa, ve sha ile birebir olculur.

FAIL-CLOSED: kanonik okunamazsa ya da iki capa TAM BIR KEZ bulunmazsa shim exec ETMEZ,
DENY basar. Yanlis eve homelenmis bir kapi sessizce calismaktansa gurultuyle durur.

Bu modul TEK KAYNAKTIR: shim metnini uretir, evleri siniflar. Kapi
(`tools/kapi-dagitim-kapisi.py`), kurucu (`tools/kapi-dagitim-kur.py`) ve kabul testi
(`tools/kapi-dagitim-test.py`) UCU DE bu modulu cagirir — ikinci bir renderer YAZILMAZ
([[ikiz-tanim-sessiz-ayrisma]]).
"""
import hashlib
import os

# CANLI MAKINEDE tek kaynak buradadir. CI kosucusunda (GitHub) bu yol YOKTUR; orada
# yalnizca MEKANIZMA olculur (fikstur evleri + mutasyon), FILO olculemez ve kabul testi
# bunu ADIYLA basar ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
CANLI_KOK = "/Users/okan/dev/pruvo"
KAYNAK_KOK = CANLI_KOK if os.path.isdir(CANLI_KOK) else os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
KAYNAK = KAYNAK_KOK + "/tools/mimar-icra-kapisi.py"
KAYNAK_TOOLS = KAYNAK_KOK + "/tools"

# === CAPALAR — GIRIS NOKTASININ GERCEKTEN OKUDUGU DEGERLER ===
# [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]: capa, kapinin davranisini
# BELIRLEYEN satir olmali. Bu ikisi oyle: REPO_ONEKI'den DURUM_YOL/D1_YOL/EV_ADI ve
# SERT_BLOK_EVLER karari turer; GIT_WORKTREE_KAYIT'ten ROL EKSENI (K318) turer.
CAPA_REPO = 'REPO_ONEKI = "/Users/okan/dev/pruvo/"'
CAPA_WT = 'GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"'

# (ad, ev koku, evin kendi settings.json'unun cagirdigi GORELI yol, mod)
# 'kaynak' = govdenin kendisi burada yasar (shim YOK, olculecek sey dosyanin VARLIGI).
# 'shim'   = evde shim durmali.
EVLER = (
    ("KraL", KAYNAK_KOK, "tools/mimar-icra-kapisi.py", "kaynak"),
    ("MaCiT", "/Users/okan/dev/pruvo-hasat", ".claude/mimar-icra-kapisi.py", "shim"),
    ("HocA", "/Users/okan/dev/pruvo-bot", ".claude/mimar-icra-kapisi.py", "shim"),
    ("TeKiN", "/Users/okan/dev/pruvo-jenerator", ".claude/mimar-icra-kapisi.py", "shim"),
    ("ArTisT", "/Users/okan/dev/pruvo-pazarlama", ".claude/mimar-icra-kapisi.py", "shim"),
    ("BaBa", "/Users/okan/dev/pruvo-advisor", ".claude/mimar-icra-kapisi.py", "shim"),
)

# Shim metninin SURUMU. Kaynak govdesi degisince BU DEGISMEZ (shim kaynaktan bagimsiz) —
# yalnizca shim'in kendi sozlesmesi degisirse artar. Kurulu shim'ler o an kirmizi yanar.
SHIM_SURUMU = "1"

SHIM_IMZASI = "# === PRUVO KAPI SHIM (uretildi: tools/kapi_dagitim.py) ==="

# Siniflar. RED olanlar: kapinin rc=1 verdigi kume.
GUNCEL = "GUNCEL"          # shim yerinde ve beklenenle BIREBIR
KAYNAK_EVI = "KAYNAK"      # govdenin kendi evi; dosya var ve derleniyor
SHIM_BAYAT = "SHIM_BAYAT"  # shim var ama beklenen metinle ayrisik
ESKI_KOPYA = "ESKI_KOPYA"  # shim degil, DONMUS tam govde kopyasi (bugunku hastalik)
YOK = "YOK"                # dosya yok
OKUNAMADI = "OKUNAMADI"    # okunamadi / cozulemedi
CAPA_KIRIK = "CAPA_KIRIK"  # kaynak evinde iki capa TAM BIR KEZ gecmiyor (filo KARARIR)

YESIL_SINIFLAR = (GUNCEL, KAYNAK_EVI)


def sha256_metin(metin):
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def sha256_dosya(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kaynak_metni():
    with open(KAYNAK, encoding="utf-8") as f:
        return f.read()


def capa_sayilari(metin):
    """Kanonik govdede iki capanin kac kez gectigi. Kurucu ve shim AYNI olcuyu kullanir."""
    return (metin.count(CAPA_REPO), metin.count(CAPA_WT))


def shim_metni(ev_adi, ev_koku):
    """Bir ev icin shim KAYNAK METNI — deterministik (zaman damgasi/rastgelelik YOK).

    Ayni (ev_adi, ev_koku) cifti icin her cagride BIREBIR ayni metni doner; bayatlik
    olcumu bu determinizme dayanir."""
    kok = ev_koku.rstrip("/")
    return (
        "#!/usr/bin/env python3\n"
        + SHIM_IMZASI + "\n"
        "# SHIM_SURUMU = \"" + SHIM_SURUMU + "\"\n"
        "# EV = \"" + ev_adi + "\"\n"
        "# EV_KOKU = \"" + kok + "\"\n"
        "#\n"
        "# BU DOSYA ELLE DUZENLENMEZ. Govde TEK YERDE yasar:\n"
        "#   /Users/okan/dev/pruvo/tools/mimar-icra-kapisi.py\n"
        "# Bu shim o govdeyi CALISMA ANINDA okur, iki ev sabitini bu evin kokune cevirir\n"
        "# ve exec eder. Kaynak degisince bu ev ANINDA guncellenir — dagitim adimi YOKTUR,\n"
        "# dolayisiyla 'kurulu kopya kaynaktan geride' hali YAPISAL OLARAK IMKANSIZDIR.\n"
        "# Yenilemek/olcmek icin (KraL evinden):\n"
        "#   python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kapisi.py --ev " + kok + "\n"
        "#\n"
        "# FAIL-CLOSED: kaynak okunamazsa ya da iki capa TAM BIR KEZ bulunmazsa exec\n"
        "# EDILMEZ, DENY basilir. Yanlis eve homelenmis kapi sessizce calismaz.\n"
        "import hashlib\n"
        "import json\n"
        "import sys\n"
        "\n"
        "EV = \"" + ev_adi + "\"\n"
        "EV_KOKU = \"" + kok + "\"\n"
        "KAYNAK = \"" + KAYNAK + "\"\n"
        "KAYNAK_TOOLS = \"" + KAYNAK_TOOLS + "\"\n"
        "CAPA_REPO = " + repr(CAPA_REPO) + "\n"
        "CAPA_WT = " + repr(CAPA_WT) + "\n"
        "\n"
        "\n"
        "def _dur(neden):\n"
        "    sys.stdout.write(json.dumps({\n"
        "        \"hookSpecificOutput\": {\n"
        "            \"hookEventName\": \"PreToolUse\",\n"
        "            \"permissionDecision\": \"deny\",\n"
        "            \"permissionDecisionReason\": (\n"
        "                \"MIMAR ICRA KAPISI KURULU DEGIL (fail-closed, ev=\" + EV + \"): \"\n"
        "                + neden + \" Kapi govdesi tek kaynaktadir: \" + KAYNAK + \". \"\n"
        "                \"Olcum: python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kapisi.py \"\n"
        "                \"--ev \" + EV_KOKU\n"
        "            ),\n"
        "        }\n"
        "    }, ensure_ascii=False) + \"\\n\")\n"
        "    sys.exit(0)\n"
        "\n"
        "\n"
        "try:\n"
        "    with open(KAYNAK, encoding=\"utf-8\") as _f:\n"
        "        _metin = _f.read()\n"
        "except Exception as _hata:\n"
        "    _dur(\"kapi govdesi OKUNAMADI (\" + repr(_hata) + \").\")\n"
        "\n"
        "if _metin.count(CAPA_REPO) != 1 or _metin.count(CAPA_WT) != 1:\n"
        "    _dur(\n"
        "        \"kapi govdesindeki EV CAPALARI TAM BIR KEZ bulunamadi (\"\n"
        "        + str(_metin.count(CAPA_REPO)) + \"/\" + str(_metin.count(CAPA_WT))\n"
        "        + \"); govde bu shim'in sozlesmesini kirmis olabilir.\"\n"
        "    )\n"
        "\n"
        "_metin = _metin.replace(CAPA_REPO, 'REPO_ONEKI = \"' + EV_KOKU + '/\"')\n"
        "_metin = _metin.replace(\n"
        "    CAPA_WT, 'GIT_WORKTREE_KAYIT = \"' + EV_KOKU + '/.git/worktrees\"')\n"
        "\n"
        "if KAYNAK_TOOLS not in sys.path:\n"
        "    sys.path.insert(0, KAYNAK_TOOLS)\n"
        "\n"
        "try:\n"
        "    sys.stderr.write(\n"
        "        \"MIMAR-KAPISI shim ev=\" + EV + \" kaynak_sha=\"\n"
        "        + hashlib.sha256(_metin.encode(\"utf-8\")).hexdigest()[:12] + \"\\n\")\n"
        "except Exception:\n"
        "    pass\n"
        "\n"
        "exec(compile(_metin, KAYNAK, \"exec\"),\n"
        "     {\"__name__\": \"__main__\", \"__file__\": KAYNAK, \"__builtins__\": __builtins__})\n"
    )


def kurulu_yol(ev_koku, goreli):
    return os.path.join(ev_koku, goreli)


def siniflandir(ev_adi, ev_koku, goreli, mod):
    """Bir evin KURULU dosyasini sinifla. Doner: (sinif, kurulu_sha, beklenen_sha).

    beklenen_sha 'kaynak' modunda None'dir (o evde shim aranmaz).
    Hicbir yerde DOSYA BOYUTU olcut DEGILDIR — eksen sha256'dir."""
    yol = kurulu_yol(ev_koku, goreli)
    if not os.path.exists(yol):
        return (YOK, None, None)
    try:
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
    except Exception:
        return (OKUNAMADI, None, None)
    kurulu = sha256_metin(icerik)

    if mod == "kaynak":
        try:
            compile(icerik, yol, "exec")
        except Exception:
            return (OKUNAMADI, kurulu, None)
        # 🔴 CAPA SOZLESMESI: bes evin shim'i BU IKI SATIRI okur. Govdede capa sayisi
        # 1'den saparsa shim'ler fail-closed DENY'a duser ve BES EV birden kararir —
        # yani bu, kaynak evinde olculmesi gereken en pahali kirilmadir.
        if capa_sayilari(icerik) != (1, 1):
            return (CAPA_KIRIK, kurulu, None)
        return (KAYNAK_EVI, kurulu, None)

    beklenen_metin = shim_metni(ev_adi, ev_koku)
    beklenen = sha256_metin(beklenen_metin)
    if kurulu == beklenen:
        return (GUNCEL, kurulu, beklenen)
    if SHIM_IMZASI in icerik:
        return (SHIM_BAYAT, kurulu, beklenen)
    return (ESKI_KOPYA, kurulu, beklenen)


def filo(evler=None):
    """Tum evleri sinifla. Doner: [(ad, kok, goreli, mod, sinif, kurulu, beklenen), ...]"""
    sonuc = []
    for ad, kok, goreli, mod in (evler if evler is not None else EVLER):
        sinif, kurulu, beklenen = siniflandir(ad, kok, goreli, mod)
        sonuc.append((ad, kok, goreli, mod, sinif, kurulu, beklenen))
    return sonuc
