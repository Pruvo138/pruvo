#!/usr/bin/env python3
"""CODEX YARDIMCISI — pahali bilissel adimlari (gorsel secme + Turkce icerik) devreder.

Amac: token diyeti. Gorsel okuma + aciklama yazma Claude'un baglamina GIRMEZ; Codex yapar,
temiz JSON doner, Claude sadece kucuk metni okur.

Kullanim:  python3 tools/thing-codex.py <thing_id> [<thing_id> ...]
Onkosul :  once  python3 tools/thing-hazirla.py <id...>  (gorselleri + meta.json'u uretir)

Her id icin `.thing-cache/<id>/meta.json` + `gN.jpg`'leri okur, Codex'e yollar, sunu doner:
  { sec_gorseller, elenen, baslik, aciklama, kategori, marka, fiyat_oneri, not }
Ciktiyi ekrana + `.thing-cache/<id>/oneri.json`'a yazar.

=== NEDEN GEMINI DEGIL (2026-07-15) ===
Gemini token basina GERCEK PARA yakiyordu: 2 gunde 2.000 TL, bakiye eksiye dusup servis durdu.
Sebep: `gemini-flash-latest` takma adi sabit model degil ("en yeni flash" demek) -> Google 3.5
Flash'i cikarinca takma ad oraya kaydi ve haberimiz olmadan 5x fiyata gectik ($1.50/$9.00 vs
$0.30/$2.50 beklenen). Codex ChatGPT abonelik limitini tuketir; 19 Tem olcumunde 230 urun +
1 jenerator haftalik limitin %38'ini harcadi. Bu nedenle varsayilan KAPALIDIR. Yalniz Okan'in
o parti icin acik izniyle `PRUVO_URUN_AI_IZNI=EVET` verilirse model cagrisi yapar.
DERS: model takma adi ("-latest") KULLANMA, surumu her zaman ACIKCA yaz. Yukseltme bilincli karar olsun.

Kimlik: `~/.codex/auth.json` (ChatGPT ile giris; `codex login`). Sir icermez; harici pip paketi YOK.
"""
import importlib.util
import json, os, re, subprocess, sys, tempfile
import unicodedata

ROOT = "/Users/okan/dev/pruvo"
IMGROOT = os.path.join(ROOT, ".thing-cache")
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

# Codex PATH'te DEGIL — ChatGPT.app icinde geliyor, tam yol sart.
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex"

# Surumu ACIKCA yaz (yukaridaki "-latest" dersi). Yukseltme bilincli karar olsun.
MODEL = "gpt-5.4-mini"      # basit is: bak + JSON don. Kalite yetmezse -> gpt-5.5
EFFORT = "low"              # Okan'in config.toml'undaki xhigh bu is icin gereksiz (yavas + kota yer)
MAX_IMG = 4                 # CLAUDE.md zaten 3-4 gorsel istiyor; cache'te 8 gorsellik urunler var
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

MARKA DILI (ZORUNLU): Sitede "3D baski" / "3D printed" IFADESI YASAK. Bunun yerine
"ozel tasarim uretim" / "ozel uretilir" de. Urun ozel siparisle uretilir mantigi.

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
  seklinde olmali (A × B × C degerlerini verilen olcuyle doldur, × isaretini kullan). "3D baski" deme.
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


def codex(prompt, imgler, cikti_yolu):
    """codex exec calistir; son mesaji cikti_yolu'na SAF JSON olarak yazar."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as sf:
        json.dump(SEMA, sf)
        sema_yolu = sf.name
    cmd = [CODEX, "exec",
           "-m", MODEL,
           "-c", "model_reasoning_effort=" + EFFORT,
           "--ephemeral",            # 700 oturum dosyasi ~/.codex/sessions'a birikmesin
           "-s", "read-only",        # is sadece "bak + JSON don"; shell/yazma gerekmiyor
           "--skip-git-repo-check",
           "--output-schema", sema_yolu,
           "-o", cikti_yolu]
    for f in imgler:
        cmd += ["-i", f]
    cmd.append("-")                  # prompt stdin'den
    try:
        for deneme in range(TRIES):
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(cikti_yolu):
                return True, ""
            hata = (r.stderr or r.stdout or "")[-300:]
            if deneme == TRIES - 1:
                return False, hata
        return False, "bilinmeyen"
    finally:
        os.unlink(sema_yolu)


def process(tid):
    d = os.path.join(IMGROOT, tid)
    mp = os.path.join(d, "meta.json")
    if not os.path.exists(mp):
        print("=== %s === ATLA: meta.json yok (once thing-hazirla.py calistir)" % tid)
        return
    meta = json.load(open(mp))
    imgs = dogal_sirala([f for f in os.listdir(d) if f.startswith("g") and f.endswith(".jpg")])
    if not imgs:
        print("=== %s === ATLA: gorsel yok" % tid)
        return
    imgs = imgs[:MAX_IMG]
    olcu = meta.get("olcu_mm")
    olcu_s = ("%d x %d x %d" % tuple(olcu)) if olcu else "yok"
    prompt = PROMPT % (", ".join(KATEGORILER), meta.get("baslik", "?"),
                       meta.get("tasarimci", "?"), meta.get("lisans", "?"), olcu_s)
    prompt += "\nGORSELLER (sirasiyla ekli): " + ", ".join(imgs) + "\n"

    onerip = os.path.join(d, "oneri.json")
    ok, hata = codex(prompt, [os.path.join(d, f) for f in imgs], onerip)
    if not ok:
        print("=== %s === Codex basarisiz: %s" % (tid, hata))
        return
    try:
        out = json.load(open(onerip))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print("=== %s === Codex gecersiz JSON dondu: %s" % (tid, e))
        if os.path.exists(onerip):
            os.unlink(onerip)   # bozuk dosya birakma — cagiran "oneri var" saniyor
        return

    # KATEGORI NORMALIZASYONU (sessiz-hata kapisi): oneri.json'u TUM ekle scriptleri
    # (urun-ekle / printables-ekle / makerworld-ekle / mmf / cgt / cults3d) okur ve degeri
    # urunler.json'a AYNEN yazar. Kanonik olmayan ad urunu kategoriden gorunmez yapar.
    ham_kat = out.get("kategori")
    kanonik = kanonik_kategori(ham_kat)
    if kanonik is None:
        print("=== %s === Codex gecersiz kategori dondu: %r (gecerli: %s)"
              % (tid, ham_kat, ", ".join(KATEGORILER)))
        os.unlink(onerip)       # fail-closed: kotu kategoriyle urun STAGE ETME
        return
    if kanonik != ham_kat:
        print("=== %s === kategori normalize edildi: %r -> %r" % (tid, ham_kat, kanonik))
        out["kategori"] = kanonik
        with open(onerip, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)

    print("=== %s === %s | %s | %s | %s" % (
        tid, out.get("baslik", "?"), out.get("kategori", "?"),
        out.get("fiyat_oneri", "?"), ", ".join(out.get("sec_gorseller", []))))


def main():
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/thing-codex.py <thing_id> [<thing_id> ...]")
    if not ai_izinli():
        sys.exit("KREDI KAPISI: urun-basi Codex cagrisi kapali. Yalniz Okan acikca izin verirse "
                 "PRUVO_URUN_AI_IZNI=EVET kullanilir.")
    if not os.path.exists(CODEX):
        sys.exit("Codex bulunamadi: %s (ChatGPT.app kurulu mu?)" % CODEX)
    for tid in sys.argv[1:]:
        process(tid)


if __name__ == "__main__":
    main()
