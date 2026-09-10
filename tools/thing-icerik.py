#!/usr/bin/env python3
"""motor YARDIMCISI — pahali bilissel adimlari (gorsel secme + Turkce icerik) devreder.

Amac: token diyeti. Gorsel okuma + aciklama yazma Claude'un baglamina GIRMEZ; motor yapar,
temiz JSON doner, Claude sadece kucuk metni okur.

Kullanim:  python3 tools/thing-icerik.py <thing_id> [<thing_id> ...]
Onkosul :  once  python3 tools/thing-hazirla.py <id...>  (gorselleri + meta.json'u uretir)

Her id icin `.thing-cache/<id>/meta.json` + `gN.jpg`'leri okur, motora yollar, sunu doner:
  { sec_gorseller, elenen, baslik, aciklama, kategori, marka, fiyat_oneri, not }
Ciktiyi ekrana + `.thing-cache/<id>/oneri.json`'a yazar.

=== NEDEN GEMINI DEGIL (2026-07-15) ===
Gemini token basina GERCEK PARA yakiyordu: 2 gunde 2.000 TL, bakiye eksiye dusup servis durdu.
Sebep: `gemini-flash-latest` takma adi sabit model degil ("en yeni flash" demek) -> Google 3.5
Flash'i cikarinca takma ad oraya kaydi ve haberimiz olmadan 5x fiyata gectik ($1.50/$9.00 vs
$0.30/$2.50 beklenen). emekli motor ChatGPT abonelik limitini tuketir; 19 Tem olcumunde 230 urun +
1 jenerator haftalik limitin %38'ini harcadi. Bu nedenle varsayilan KAPALIDIR. Yalniz Okan'in
o parti icin acik izniyle `PRUVO_URUN_AI_IZNI=EVET` verilirse model cagrisi yapar.
DERS: model takma adi ("-latest") KULLANMA, surumu her zaman ACIKCA yaz. Yukseltme bilincli karar olsun.

=== PORT: EMEKLI CLI -> CANLI MOTOR (2026-09-10, K399) ===
Bu arac 9 Eyl'e kadar emekli bir CLI alt sureci (`codex exec`) calistiriyordu; o ad
KANONIK KAYITTA EMEKLIDIR (`tools/mimar_kimlik.py` EMEKLI_ISCI_MOTORLARI) ve makinenin
yerel ayari adiyla REDDEDILMIS bir alt modele bakiyordu -> model sabitini "duzeltmek" ariza
mesajini susturur ama EMEKLI MOTORU DIRILTIRDI ([[tek-satir-duzelt-hukmu-emekli-
bagimliliga-dayaniyorsa-porttur]]). Bu yuzden sabit degil TASIYICI degisti: artik
CANLI kumenin ucuna (Anthropic uyumlu /v1/messages) DOGRUDAN HTTP cagrisi yapilir.
Motor ADI `mimar_kimlik.CANLI_ISCI_MOTORLARI`den, UC AYARI isci hattinin uc
tablosundan TURETILIR; bu dosyada ikinci bir motor listesi YOKTUR.

TASINAN KABILIYETLER (olculdu 10 Eyl, gercek uca karsi):
  * semali JSON  : `--output-schema` -> arac (tool) semasi + zorunlu arac secimi.
                   KISMEN: sema araca baglaniyor ama ZORLAMA KARARSIZ — 7 gercek
                   cagrinin 5'i arac blogu yerine ayni JSON'u METIN dondurdu. Bu
                   yuzden sozlesme UZAK UCA BIRAKILMADI: `sema_ihlali()` yerel ve
                   deterministik dogrulama yapar, iki tasiyici da ayni kapidan gecer.
  * gorsel girdi : `-i <dosya>` (coklu) -> base64 image blogu. CALISIYOR — kor-model
                   testinde gorsele basilan 5 haneli rastgele sayi 5/5 dogru okundu
                   (200 + akici cevap TEK BASINA gorme kaniti DEGILDIR: gorselsiz
                   taban probu da akici bir "gorsel aciklamasi" UYDURDU).
  * cikti yolu   : `-o <yol>` -> yaniti dosyaya bu arac yazar.
  * yeniden deneme: TRIES aynen korundu.
DUSEN KABILIYET (sessizce atlanmadi, ADIYLA yaziliyor):
  * `model_reasoning_effort=low` (eski EFFORT sabiti) — yeni ucun Anthropic uyumlu
    yuzeyinde karsiligi OLCULEMEDI. Islevsel etkisi yok (o bayrak kota/hiz ayariydi,
    cikti sozlesmesini belirlemiyordu); yine de DUSMUS kabiliyet olarak kayda gecer.
O CLI'ya ozgu `--ephemeral` / `-s read-only` / `--skip-git-repo-check` bayraklari
KONUSUZ kaldi: dogrudan HTTP cagrisinda oturum dosyasi birikmez ve kabuk acilmaz.

Kimlik: uc anahtari isci hattinin anahtar dosyasindan OKUNUR (bu dosyada sir YOKTUR;
yol da elle yazilmaz, uc tablosundan turetilir). Harici pip paketi YOK.
"""
import importlib.util
import base64, json, os, re, sys, urllib.error, urllib.request
import unicodedata

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
# VERI KOKU: gorsel onbellegi (`.thing-cache`) DAIMA ANA kopyada durur, ama kok SABIT
# YAZILMAZ — sabit "<gelistirici-evi>/depo" CI kosucusunda YOKTUR (7 Agu 2026: ayni desen
# serit-a3'u kirmizi yakip yayini 4+ saat kapatti; yerelde HIC kirmizi yanmaz). veri_kok
# git'e sorar: worktree'de ANA kopyayi, temiz klonda/CI'da klonun kokunu dondurur.
_vkspec = importlib.util.spec_from_file_location("veri_kok",
                                                os.path.join(TOOLS_DIR, "veri_kok.py"))
_vk = importlib.util.module_from_spec(_vkspec); _vkspec.loader.exec_module(_vk)
_KOD_KOK, ROOT, _KOK_UYARI = _vk.cozumle(__file__)
if _KOK_UYARI:
    sys.stderr.write(_KOK_UYARI)
IMGROOT = os.path.join(ROOT, ".thing-cache")

# === MOTOR KIMLIGI: TURETILIR, ELLE YAZILMAZ ===============================
# Motor ADI kanonik kayittan gelir. Buraya literal bir motor adi YAZILMAZ: ikiz
# tanim sessizce ayrisir ve bu arac bir gun EMEKLI bir uca konusur — zaten bu
# dosyanin 9 Eyl arizasi tam olarak buydu.
def _canli_motor_adi():
    yol = os.path.join(TOOLS_DIR, "mimar_kimlik.py")
    spec = importlib.util.spec_from_file_location("mimar_kimlik_ti", yol)
    if spec is None or spec.loader is None:
        sys.exit("HATA: tools/mimar_kimlik.py yuklenemedi: " + yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    canli = tuple(mod.CANLI_ISCI_MOTORLARI)
    if not canli:
        sys.exit("HATA: CANLI_ISCI_MOTORLARI BOS — canli motor yok, cagri YAPILMAZ.")
    return canli[0]


CANLI_MOTOR = _canli_motor_adi()

# Uc tablosu: isci hattinin TEK kaynagi. Kopyasi BURAYA cikarilmaz.
UC_TABLOSU = os.path.expanduser("~/.claude/cron/isci-motor-uc.zsh")
UC_ANAHTAR_ALANLARI = ("MOTOR_BASE_URL", "MOTOR_ANAHTAR_DOSYASI", "MOTOR_MODEL")
ZAMAN_ASIMI = 300
MAX_TOKEN = 4000
# DENETIM UST SINIRI (motora GONDERILEN gorsel sayisi). Eskiden 4'tu -> pratikte SADECE ilk 4
# gorsel yargilaniyordu; g5+ hic gonderilmiyor, hic gorulmuyordu (backfill'de 36 g5+ gorsel
# DENETIMSIZ vitrine girdi). Gorsel okuma EN PAHALI adim (kota) -> sinirsiz genisletme yerine
# makul bir tavan: cache'te en fazla 8 gorsellik urun var, 8 gercek galerilerin tamamini kapsar.
# 8'i asan (nadir) gorsel SESSIZCE atilmaz -> denetim_birlestir() "denetlenmedi" isaretler.
MAX_IMG = 8
TRIES = 2


def ai_izinli():
    """Urun-basi model cagrisi sadece Okan'in o parti icin acik izniyle acilir."""
    return os.environ.get("PRUVO_URUN_AI_IZNI") == "EVET"

def _kategori_kapisi():
    """tools/kategori-kapisi.py'yi modul olarak yukler (dosya adinda tire var -> importlib)."""
    yol = os.path.join(TOOLS_DIR, "kategori-kapisi.py")
    spec = importlib.util.spec_from_file_location("kategori_kapisi", yol)
    if spec is None or spec.loader is None:
        sys.exit("HATA: tools/kategori-kapisi.py yuklenemedi: " + yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# TEK KAYNAK: kategori listesi BURADA TUTULMAZ. index.html + tools/build.py'den okunur
# (kategori-kapisi.py ikisini karsilastirir, ayrismislarsa duser). GIZLI kategoriler
# (Jeneratör = parametrik/sari seri) AI secimine KAPALI — o seri elle kurgulanir.
_KAPI = _kategori_kapisi()
_GIZLI = _KAPI.kaynak_listeler()[1]
KATEGORILER = [k for k in _KAPI.gecerli_kategoriler() if k not in _GIZLI]


def _katla(s):
    """Turkce diakritikleri duselerek karsilastirma anahtari uretir ('Bahçe' -> 'bahce')."""
    s = (s or "").replace("ı", "i").replace("I", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold().strip()


# Model ASCII'ye dusmus bir varyant dondururse ("Bahce") kanonik ada geri esle.
# Harita KATEGORILER'den TURETILIR — ikinci kopya liste yazilmaz.
_KANONIK = {_katla(k): k for k in KATEGORILER}


def kanonik_kategori(deger):
    """Model ciktisindaki kategoriyi kanonik ada cevirir; taninmiyorsa None doner.

    NEDEN: bu deger urunler.json'a AYNEN yazilir ve index.html cipi `p.kategori === activeCat`
    ile BIREBIR esler. 'Bahce' (ASCII) gibi bir varyant urunu kategoriden GORUNMEZ yapar
    (sessiz hata; 2 urunde yasandi) -> tek darbogazda burada normalize edilir.
    """
    return _KANONIK.get(_katla(deger))

# --output-schema: cikti seklini modele ZORLA (Gemini'deki responseMimeType=json'un karsiligi).
SEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["sec_gorseller", "elenen", "baslik", "aciklama", "kategori",
                 "marka", "fiyat_oneri", "not"],
    "properties": {
        "sec_gorseller": {"type": "array", "items": {"type": "string"}},
        "elenen": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["dosya", "neden"],
            "properties": {"dosya": {"type": "string"}, "neden": {"type": "string"}}}},
        "baslik": {"type": "string"},
        "aciklama": {"type": "string"},
        "kategori": {"type": "string", "enum": KATEGORILER},
        "marka": {"type": "array", "items": {"type": "string"}},
        "fiyat_oneri": {"type": "string"},
        "not": {"type": "string"},
    },
}

PROMPT = """Sen PRUVO adli endustriyel parca uretim firmasinin urun-listeleme yardimcisisin.
Sana bir kaynak urunun ingilizce basligi, tasarimci/lisans bilgisi, olcusu ve N adet galeri
gorseli verilecek. Gorevin: (1) en iyi gorselleri secmek, (2) Turkce urun icerigi yazmak.

MARKA DILI (ZORUNLU) — DIZGE DEGIL SINIF: PRUVO'nun URETIM SURECINE dair HICBIR dil
gecmez. Metin urunun NE OLDUGUNU ve NEYE UYDUGUNU anlatir, NASIL yapildigini ANLATMAZ.
YASAK SINIF (liste KAPALI DEGIL, akil yurut):
  * "3D baski" / "3D printed"
  * "basil-" kokunun HER kipi: basilir, basilan, basilacak, basilmasi, basilmadan, basim
  * "baski" isminin surec cekimleri: baski sonrasi, baskida olcu/olcek, test baskisi,
    baskiyla uretilen, dekoratif baski modeli, baski muhafaza/kutu
  * dilimleyici/makine dili: dolgu orani, katman yuksekligi, destek, filament, nozul capi,
    duvar/kabuk sayisi, brim/raft, FDM/SLA/infill, Cura/PrusaSlicer
  * dosya dili: STL, 3MF, gcode, "dosya dahildir"
  * makine parki: "bazi yazicilarda", "baski yatagina sigar"
  * malzeme TAVSIYESI ureticiye: "PETG onerilir"
DOGRU YAZIM: "ozel tasarim uretim" / "ozel uretilir". Urun ozel siparisle uretilir mantigi.
Kanonik karsiliklar (anlami KORU, cumleyi KISALTMA):
  "<sifat> malzemeden basilir."            -> "<sifat> malzemeden uretilir."
  "<sifat> malzemeden basilmasi onerilir." -> "<sifat> malzemeden uretilmesi onerilir."
  "ince ama saglam basilir."               -> "ince ama saglam uretilir."
  "dekoratif baski modeli"                 -> "dekoratif modeli"
SERBEST (bunlar IHLAL DEGIL, DUZELTME):
  * malzeme BEYANI: "PETG malzemededir" (tavsiye degil, beyan)
  * BASMA anlami: "dugmeye kazara basilmasini onler", "ayakla basilan pedal"
  * BASINC anlami: "baskiyla oturur", "yay baskisi", "baski balatasi/takozu/aparati"

--- GOREV 1: GORSEL SECIMI ---
3-4 iyi gorsel sec (varsa). Kurallar:
- Gercek/araca-takili/elde-tutulan FOTOGRAFLARI tercih et (guven verir). Sadece render varsa temiz render.
- ELE: tasarimci logosu/filigrani, uzerinde yazi/CAD arayuzu olan (or. "Gemini" parilti/logo), cok
  kucuk/bozuk, birebir duplike, alakasiz gorsel.
- DIKKAT: Ayni sete dahil AYRI parca (stand/tutucu/aparat/aksesuar) "alakasiz" DEGILDIR — onu DAHIL et
  (urunun setini gosterir). Sadece gercekten ilgisiz gorseli ele.
- sec_gorseller: dosya adlari (or. "g1.jpg"), EN IYI ilk sirada. elenen: {dosya, neden} (neden 1-2 kelime).

--- GOREV 2: TURKCE ICERIK ---
- baslik: kisa, net Turkce. Parca adi + varsa marka/model. Abartma yok.
- aciklama: ferah, TARANABILIR. Kisa 1-2 cumle giris + ardindan '\\n' ile ayrilmis kisa maddeler
  (ne ise yarar, nasil kullanilir, montaj). Gorsel/basliktan EMIN OLMADIGIN ozelligi UYDURMA.
  Olcu verildiyse aciklamanin SONUNA aynen su satiri (DUZGUN TURKCE, diakritikli) ekle:
  "Yaklasik dis olculer: A × B × C mm." -> yani cikti "Yaklaşık dış ölçüler: A × B × C mm."
  seklinde olmali (A × B × C degerlerini verilen olcuyle doldur, × isaretini kullan).
  Yukaridaki MARKA DILI sinif kuralina UY — "3D baski" DEMEMEK YETMEZ, surec dilinin tamami yasak.
- kategori: SADECE su listeden BIREBIR bir ad (harfi harfine kopyala; Turkce karakterleri
  ASCII'ye DUSURME — "Bahçe" yaz, "Bahce" DEGIL): %s
  Secim kurali (urunun ait oldugu alan / calisma prensibi):
  * Arac/marka-OZEL parca -> ilgili arac kategorisine (Otomobil/Motosiklet/Bisiklet/Marin), Tamirat'a DEGIL.
  * ONEMLI TEST — urun aracin KENDISI icin mi (parca/aksesuar), yoksa aracin TEMSILI mi (maketi/resmi)?
    - Araçla kullanilan parca VEYA aksesuar -> Otomobil. Araca monte olmasi SART DEGIL: buz kaziyici,
      bardaklik, telefon tutucu, anahtar kilifi, huni, cam suyu kapagi da Otomobil'dir.
    - Aracin TEMSILI olan sey (model/maket araba, olcekli model, Lego uyumlu govde, RC govdesi)
      -> Oyun/Hobi. Duvar dekoru/siluet/tablo/kumbara/sus -> Dekorasyon.
    - Tamirat SADECE marka-BAGIMSIZ genel atolye aleti icindir; marka adi gecen urunu Tamirat'a KOYMA.
  * Tamirat: marka-BAGIMSIZ genel tamir/atolye aleti (mengene, kelepce, klips, tirtikli civata vb.).
  * Kamera: kameraya dair HER sey (GoPro/aksiyon kamera, montaj, tripod, lens aksesuari) -> Elektronik'e degil.
  * Elektronik: elektrik/pille calisan cihaz parcasi (kahve makinesi, buzdolabi, supurge, 3D yazici) -
    kamera HARIC, e-bike HARIC.
  * Bisiklet: bisiklet + e-bike parcalari (e-bike Elektronik'e DEGIL).
  * Ev: elektriksiz ev esyasi. Ofis: ofis/kirtasiye. "Bahçe": bahce/guc ekipmani. Dekorasyon: sus.
    Oyun/Hobi: oyuncak/hobi/koleksiyon. Marin: tekne/denizcilik.
- marka: DIZI. Basliktaki/urundeki marka veya model adlari (or. ["Audi","Volkswagen"]). Jenerik urunse [].
- fiyat_oneri: KABA bir baslangic fiyati (or. "400 TL"). PRUVO ozel-uretim yedek parca satar; kucuk
  tekil parca genelde ~200-600 TL, buyuk/coklu-parca/set ~600-1200 TL. Sadece baslangic tahmini —
  insan sonra ayarlayacak. Emin degilsen orta bir deger ver.

--- KAYNAK BILGISI ---
Kaynak baslik: %s
Tasarimci   : %s
Lisans      : %s
Olcu (mm)   : %s

CIKTI: SADECE su semada gecerli JSON dondur (markdown/backtick YOK):
{"sec_gorseller":["g1.jpg"],"elenen":[{"dosya":"g2.jpg","neden":"logo"}],
 "baslik":"...","aciklama":"...","kategori":"Otomobil","marka":["..."],
 "fiyat_oneri":"400 TL","not":"kisa gerekce"}
"""


def dogal_sirala(dosyalar):
    """g1, g2, ... g10 — duz sorted() g10'u g2'den once koyar."""
    return sorted(dosyalar, key=lambda f: int(re.sub(r"\D", "", f) or 0))


def denetim_bol(imgs, cap):
    """Dogal sirali galeriyi motora GONDERILEN (denetlenecek) ve GONDERILMEYEN diye ikiye boler.

    Eski hata: `imgs[:MAX_IMG]` kirpiliyor ama kirpilan gorsel HICBIR YERDE kayda gecmiyordu ->
    g5+ sessizce denetim disi kaliyordu. cap kadari gonderilir, kalani `denetim_birlestir` ile
    ACIKCA 'denetlenmedi' isaretlenir (sessiz kirpma YASAK)."""
    imgs = dogal_sirala(imgs)
    return imgs[:cap], imgs[cap:]


def denetim_birlestir(all_imgs, cap, out):
    """motor ciktisina (out) 'denetlenmedi' alanini ekler ve GARANTI eder: her galeri gorseli
    ya sec_gorseller/elenen ya da denetlenmedi altinda gorunur (union == tum galeri).

    Iki denetim-disi kaynagi kapsar:
      1. cap ustu (motora HIC gonderilmedi)  -> neden "kota ust siniri (denetlenmedi)"
      2. gonderildi ama motor ne secti ne eledi -> neden "motor kapsamadi (denetlenmedi)"
         (fail-loud: gorulmemis/atlanmis gorsel sessizce vitrine girmesin)."""
    all_imgs = dogal_sirala(all_imgs)
    gonderilen, gonderilmeyen = denetim_bol(all_imgs, cap)
    kapsanan = set(out.get("sec_gorseller") or [])
    for e in (out.get("elenen") or []):
        if isinstance(e, dict) and e.get("dosya"):
            kapsanan.add(e["dosya"])
    denetlenmedi = []
    for f in gonderilmeyen:
        denetlenmedi.append({"dosya": f, "neden": "kota ust siniri (denetlenmedi)"})
    for f in gonderilen:
        if f not in kapsanan:
            denetlenmedi.append({"dosya": f, "neden": "motor kapsamadi (denetlenmedi)"})
    out["denetlenmedi"] = denetlenmedi
    return out


# =============================================================================
# K398 — CIKISI RC'DEN DEGIL ICERIKTEN YARGILA (fail-open kapatmasi)
# =============================================================================
# UC KOL AYNEN KORUNDU, TASIYICI DEGISTI (10 Eyl 2026 portu):
#   kol-1 "rc"      : alt surec rc'si  ->  HTTP DURUM KODU (durum == 200)
#   kol-2 "yazildi" : cikti dosyasi VAR mi (bayat kapisi her denemeden ONCE siler)
#   kol-3 "govde"   : HAM yanit govdesinde API hata izi VAR mi (durum'a BAKMAZ)
# Kollarin BAGIMSIZ kalmasi sarttir; birbirinden turetilirse ayni korlugu
# paylasirlar ([[oz-denetim-ayni-ayraci-kullanirsa-korlesir]]) ve K398 fail-open
# kapatmasi kagit uzerinde kalir.
#
# PORT OLCUMU (10 Eyl, gercek uca karsi 4 hata probu): asagidaki desen yeni motorun
# HTTP-duzeyi hata govdelerine UYUYOR — 400 (bos messages) ve 401 (gecersiz anahtar)
# yanitlarinin ikisi de `"type":"error"` tasidi, desen ikisini de yakaladi.
# EKLENEN KOL (`status_code`): bu ucun yanit zarfinda `base_resp.status_code` diye
# IC-BANT bir hata kanali var. Basarili yanitta 0 gelir; SIFIR OLMAYAN bir deger
# HTTP 200 ile birlikte gelebilir — yani tam olarak K398'in kapattigi fail-open
# sinifi. 4 probda tetiklenmedi (OLCULEMEDI), o yuzden kol ONCEDEN kuruldu:
# olculmemis bir kanali acik birakmak, olculmus bir kolu sokmekle ayni sonuca varir.
# `(?!0[\s,}])` sarti basarili yanitin `"status_code":0`'ini YANLIS-POZITIF yapmaz.
_HATA_DESEN = re.compile(r'"type"\s*:\s*"error"|invalid_request_error|'
                         r'"status"\s*:\s*[45]\d\d|'
                         r'"status_code"\s*:\s*(?!0[\s,}])\d+', re.I)


def hata_govdesi(stdout, stderr):
    """CLI ciktisinda API HATA govdesi var mi? -> eslesen parca | None.

    DURUM KODUNA BAKMAZ: bu kol kol-1'den BAGIMSIZ olmali, yoksa ikisi ayni korlugu
    paylasir ([[oz-denetim-ayni-ayraci-kullanirsa-korlesir]]). Imza (a, b) ciftidir:
    eski hatta (stdout, stderr), yeni hatta (ham_govde, "") gecilir — komsu testler
    bu imzaya capalidir, DEGISTIRME."""
    m = _HATA_DESEN.search((stdout or "") + "\n" + (stderr or ""))
    return m.group(0) if m else None


ARAC_ADI = "urun_icerigi"
_MEDYA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
          ".webp": "image/webp", ".gif": "image/gif"}


def _uc_ayari():
    """CANLI motorun uc ayarini TEK KAYNAKTAN (isci hattinin uc tablosu) okur.

    (base_url, anahtar_dosyasi, model) doner. Buraya ikinci bir motor tablosu
    KOPYALANMAZ: ikiz tanim sessizce ayrisir ve bir gun bu arac yanlis/emekli bir
    uca konusur. Fail-closed: tablo ya da alan yoksa cagri HIC yapilmaz."""
    if not os.path.exists(UC_TABLOSU):
        sys.exit("HATA: uc tablosu yok: %s — '%s' ucu OLCULEMEDI, cagri YAPILMADI."
                 % (UC_TABLOSU, CANLI_MOTOR))
    metin = open(UC_TABLOSU, encoding="utf-8").read()
    kok = os.path.dirname(UC_TABLOSU)
    deger = {}
    for alan in UC_ANAHTAR_ALANLARI:
        m = re.search(re.escape(alan) + r"\[" + re.escape(CANLI_MOTOR) + r"\]=(.+)", metin)
        if not m:
            sys.exit("HATA: uc tablosunda %s[%s] YOK (%s) — cagri YAPILMADI."
                     % (alan, CANLI_MOTOR, UC_TABLOSU))
        v = m.group(1).strip().strip("'\"")
        deger[alan] = v.replace("$CRON_KOKU", kok).replace("${CRON_KOKU}", kok)
    return (deger["MOTOR_BASE_URL"], deger["MOTOR_ANAHTAR_DOSYASI"], deger["MOTOR_MODEL"])


def _uc_istek(govde):
    """Uca TEK POST atar; (http_durum, HAM govde metni) doner. AG DIKISI.

    AYRI fonksiyon olmasinin sebebi olcumdur: kabul/mutasyon testleri bu dikisi
    sahteleyip K398'in uc kolunu AG OLMADAN yargilayabilsin (eski hatta bu dikis
    `subprocess.run` idi). Buradan YUKARI hicbir karar verilmez — sadece tasima."""
    base, anahtar_yolu, _model = _uc_ayari()
    if not os.path.exists(anahtar_yolu):
        return -1, '{"type":"error","error":{"type":"authentication_error",' \
                   '"message":"uc anahtar dosyasi yok"}}'
    anahtar = open(anahtar_yolu, encoding="utf-8").read().strip()
    istek = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=json.dumps(govde).encode("utf-8"),
        headers={"content-type": "application/json", "x-api-key": anahtar,
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                  # ag/DNS/zaman asimi
        return -1, '{"type":"error","error":{"type":"transport_error",' \
                   '"message":%s}}' % json.dumps(repr(e))


_TIPLER = {"string": str, "array": list, "object": dict}


def sema_ihlali(deger):
    """SEMA sozlesmesini DETERMINISTIK dogrular; ihlal metni | None doner.

    NEDEN YEREL: bu ucun `tool_choice` zorlamasi KARARSIZ olctu (7 cagrinin 5'i
    semali arac blogu yerine METIN dondu). Sozlesmeyi uzak ucun iyi niyetine
    birakirsak bir gun eksik alanli/serbest metinli bir cikti sessizce gecer ve
    urunler.json'a kadar iner. Kapi burada, BIZDE."""
    if not isinstance(deger, dict):
        return "kok nesne degil: %s" % type(deger).__name__
    for alan in SEMA["required"]:
        if alan not in deger:
            return "zorunlu alan YOK: %s" % alan
    for alan, kural in SEMA["properties"].items():
        if alan not in deger:
            continue
        beklenen = _TIPLER.get(kural.get("type"))
        if beklenen is not None and not isinstance(deger[alan], beklenen):
            return "alan tipi yanlis: %s (%s bekleniyordu)" % (alan, kural.get("type"))
        if kural.get("enum") is not None and deger[alan] not in kural["enum"]:
            # Kategori ASCII'ye dusmus olabilir -> kanonik esleme SONRA kosar; burada
            # yalnizca "hic taninmiyor" halini reddet.
            if kanonik_kategori(deger[alan]) is None:
                return "alan liste disi: %s=%r" % (alan, deger[alan])
    return None


def _metin_json(d):
    """Arac blogu gelmediginde METIN bloklarindan JSON cikarir (markdown citi dahil)."""
    metin = "".join(p.get("text", "") for p in (d.get("content") or [])
                    if isinstance(p, dict) and p.get("type") == "text").strip()
    if metin.startswith("```"):
        metin = re.sub(r"^```[a-zA-Z]*\s*", "", metin)
        metin = re.sub(r"```\s*$", "", metin).strip()
    bas, son = metin.find("{"), metin.rfind("}")
    if bas < 0 or son <= bas:
        return None
    try:
        return json.loads(metin[bas:son + 1])
    except ValueError:
        return None


def _sema_blogunu_yaz(ham, cikti_yolu):
    """Yanittaki SEMALI icerigi cikti_yolu'na SAF JSON yazar. Yazdiysa True.

    IKI YOL, TEK KAPI: once arac (tool_use) blogu aranir; yoksa metin blogu JSON
    olarak ayristirilir. AMA her iki yol da AYNI `sema_ihlali()` dogrulamasindan
    gecer — metin yolu bir GEVSEKLIK DEGIL, ayni sozlesmenin ikinci tasiyicisidir.

    🔴 Bu adim diger iki koldan BAGIMSIZ kosar: durum koduna da hata govdesine de
    BAKMAZ. Yazimi 'zaten basarili' oldugumuz duruma baglarsak kol-2 kol-1/kol-3'un
    tekrari olur ve uc kol tek kola coker."""
    try:
        d = json.loads(ham)
    except (ValueError, TypeError):
        return False
    if not isinstance(d, dict):
        return False
    icerik = None
    for p in (d.get("content") or []):
        if isinstance(p, dict) and p.get("type") == "tool_use" and p.get("name") == ARAC_ADI:
            icerik = p.get("input")
            break
    if icerik is None:
        icerik = _metin_json(d)
    if icerik is None or sema_ihlali(icerik) is not None:
        return False
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(icerik, f, ensure_ascii=False)
    return True


def motor_cagir(prompt, imgler, cikti_yolu):
    """CANLI motoru cagirir; semali yaniti cikti_yolu'na SAF JSON olarak yazar.

    Eski ad `emekli_motor_cagir` idi; tasiyici emekli CLI'dan canli uca gecince ad da
    tasindi ve KOMSU testlerin capalari AYNI turda guncellendi (bayat capa mutasyon
    bataryasini sessizce ETKISIZ birakir, [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]])."""
    _base, _anahtar, model = _uc_ayari()
    icerik = []
    for f in imgler:
        tur = _MEDYA.get(os.path.splitext(f)[1].lower(), "image/jpeg")
        with open(f, "rb") as fh:
            icerik.append({"type": "image", "source": {
                "type": "base64", "media_type": tur,
                "data": base64.b64encode(fh.read()).decode("ascii")}})
    icerik.append({"type": "text", "text": prompt})
    istek = {"model": model, "max_tokens": MAX_TOKEN,
             # `--output-schema` KARSILIGI: sema araca baglanir ve arac secimi ZORUNLU
             # kilinir -> model serbest metin/markdown DONEMEZ.
             "tools": [{"name": ARAC_ADI,
                        "description": "Secilen gorseller + Turkce urun icerigi.",
                        "input_schema": SEMA}],
             "tool_choice": {"type": "tool", "name": ARAC_ADI},
             "messages": [{"role": "user", "content": icerik}]}
    for deneme in range(TRIES):
        # BAYAT CIKTI KAPISI (K398-b): dosyanin VARLIGI bu DENEMENIN kaniti OLSUN.
        # Dongunun ICINDE: yoksa 1. denemenin yazdigi dosya 2. denemenin kol-2'sini
        # sahte yesile boyar (eski hatta dongu disindaydi; port bunu daraltmadi).
        if os.path.exists(cikti_yolu):
            os.unlink(cikti_yolu)
        durum, ham = _uc_istek(istek)
        govde = hata_govdesi(ham, "")
        _sema_blogunu_yaz(ham, cikti_yolu)
        # UC KOL, HEPSI ZORUNLU: durum temiz + cikti YAZILDI + yanitta hata govdesi YOK.
        # `govde is None` kolu K398'in kapatmasidir: durum yalan soylerse burasi tutar.
        if durum == 200 and os.path.exists(cikti_yolu) and govde is None:
            return True, ""
        if govde is not None and os.path.exists(cikti_yolu):
            # Hata govdesi VARKEN yazilmis dosya birakma — cagiran "oneri var" sanar.
            os.unlink(cikti_yolu)
        hata = (("API HATA GOVDESI: " + govde + " | ") if govde else "") + \
               ("durum=%s " % durum) + (ham or "")[-300:]
        if deneme == TRIES - 1:
            return False, hata
    return False, "bilinmeyen"


def process(tid):
    d = os.path.join(IMGROOT, tid)
    mp = os.path.join(d, "meta.json")
    if not os.path.exists(mp):
        print("=== %s === ATLA: meta.json yok (once thing-hazirla.py calistir)" % tid)
        return
    meta = json.load(open(mp))
    galeri = dogal_sirala([f for f in os.listdir(d) if f.startswith("g") and f.endswith(".jpg")])
    if not galeri:
        print("=== %s === ATLA: gorsel yok" % tid)
        return
    imgs, kirpilan = denetim_bol(galeri, MAX_IMG)
    if kirpilan:
        # SESSIZ KIRPMA YASAK: ust siniri asan gorseller LOG'lanir + asagida denetim_birlestir
        # ile oneri.json'a "denetlenmedi" olarak isaretlenir (vitrine sessizce girmesin).
        print("=== %s === UYARI: %d gorsel denetim ust siniri (%d) disi kaldi -> denetlenmedi: %s"
              % (tid, len(kirpilan), MAX_IMG, ", ".join(kirpilan)))
    olcu = meta.get("olcu_mm")
    olcu_s = ("%d x %d x %d" % tuple(olcu)) if olcu else "yok"
    prompt = PROMPT % (", ".join(KATEGORILER), meta.get("baslik", "?"),
                       meta.get("tasarimci", "?"), meta.get("lisans", "?"), olcu_s)
    prompt += "\nGORSELLER (sirasiyla ekli): " + ", ".join(imgs) + "\n"

    onerip = os.path.join(d, "oneri.json")
    ok, hata = motor_cagir(prompt, [os.path.join(d, f) for f in imgs], onerip)
    if not ok:
        print("=== %s === motor basarisiz: %s" % (tid, hata))
        return
    try:
        out = json.load(open(onerip))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print("=== %s === motor gecersiz JSON dondu: %s" % (tid, e))
        if os.path.exists(onerip):
            os.unlink(onerip)   # bozuk dosya birakma — cagiran "oneri var" saniyor
        return

    # KATEGORI NORMALIZASYONU (sessiz-hata kapisi): oneri.json'u TUM ekle scriptleri
    # (urun-ekle / printables-ekle / makerworld-ekle / mmf / cgt / cults3d) okur ve degeri
    # urunler.json'a AYNEN yazar. Kanonik olmayan ad urunu kategoriden gorunmez yapar.
    ham_kat = out.get("kategori")
    kanonik = kanonik_kategori(ham_kat)
    if kanonik is None:
        print("=== %s === motor gecersiz kategori dondu: %r (gecerli: %s)"
              % (tid, ham_kat, ", ".join(KATEGORILER)))
        os.unlink(onerip)       # fail-closed: kotu kategoriyle urun STAGE ETME
        return
    if kanonik != ham_kat:
        print("=== %s === kategori normalize edildi: %r -> %r" % (tid, ham_kat, kanonik))
        out["kategori"] = kanonik

    # DENETIM KAPSAMI (sessiz g5+ kapisi): TUM galeriye karsi kapsam hesapla; denetlenmeyen
    # (cap ustu ya da motorun kapsamadigi) gorselleri "denetlenmedi" ile ISARETLE. oneri.json'u
    # bu alanla HER ZAMAN yeniden yaz (kategori normalize olmasa da denetlenmedi guncel olsun).
    out = denetim_birlestir(galeri, MAX_IMG, out)
    with open(onerip, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    dn = out.get("denetlenmedi") or []
    dn_s = ("  DENETLENMEDI: " + ", ".join(x["dosya"] for x in dn)) if dn else ""
    print("=== %s === %s | %s | %s | %s%s" % (
        tid, out.get("baslik", "?"), out.get("kategori", "?"),
        out.get("fiyat_oneri", "?"), ", ".join(out.get("sec_gorseller", [])), dn_s))


def main():
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/thing-icerik.py <thing_id> [<thing_id> ...]")
    if not ai_izinli():
        sys.exit("KREDI KAPISI: urun-basi motor cagrisi kapali. Yalniz Okan acikca izin verirse "
                 "PRUVO_URUN_AI_IZNI=EVET kullanilir.")
    _uc_ayari()   # FAIL-CLOSED: uc/anahtar okunamiyorsa TEK urun bile islenmez
    for tid in sys.argv[1:]:
        process(tid)


if __name__ == "__main__":
    main()
