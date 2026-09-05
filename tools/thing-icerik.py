#!/usr/bin/env python3
"""emekli motor YARDIMCISI — pahali bilissel adimlari (gorsel secme + Turkce icerik) devreder.

Amac: token diyeti. Gorsel okuma + aciklama yazma Claude'un baglamina GIRMEZ; emekli motor yapar,
temiz JSON doner, Claude sadece kucuk metni okur.

Kullanim:  python3 tools/thing-icerik.py <thing_id> [<thing_id> ...]
Onkosul :  once  python3 tools/thing-hazirla.py <id...>  (gorselleri + meta.json'u uretir)

Her id icin `.thing-cache/<id>/meta.json` + `gN.jpg`'leri okur, emekli motor'e yollar, sunu doner:
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

Kimlik: `~/.codex/auth.json` (ChatGPT ile giris; `emekli motor login`). Sir icermez; harici pip paketi YOK.
"""
import importlib.util
import json, os, re, subprocess, sys, tempfile
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

# emekli motor PATH'te DEGIL — ChatGPT.app icinde geliyor, tam yol sart.
EMEKLI_MOTOR_IKILI = "/Applications/ChatGPT.app/Contents/Resources/codex"

# Surumu ACIKCA yaz (yukaridaki "-latest" dersi). Yukseltme bilincli karar olsun.
MODEL = "gpt-5.4-mini"      # basit is: bak + JSON don. Kalite yetmezse -> gpt-5.5
EFFORT = "low"              # Okan'in config.toml'undaki xhigh bu is icin gereksiz (yavas + kota yer)
# DENETIM UST SINIRI (emekli motor'e GONDERILEN gorsel sayisi). Eskiden 4'tu -> pratikte SADECE ilk 4
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
    """Dogal sirali galeriyi emekli motor'e GONDERILEN (denetlenecek) ve GONDERILMEYEN diye ikiye boler.

    Eski hata: `imgs[:MAX_IMG]` kirpiliyor ama kirpilan gorsel HICBIR YERDE kayda gecmiyordu ->
    g5+ sessizce denetim disi kaliyordu. cap kadari gonderilir, kalani `denetim_birlestir` ile
    ACIKCA 'denetlenmedi' isaretlenir (sessiz kirpma YASAK)."""
    imgs = dogal_sirala(imgs)
    return imgs[:cap], imgs[cap:]


def denetim_birlestir(all_imgs, cap, out):
    """emekli motor ciktisina (out) 'denetlenmedi' alanini ekler ve GARANTI eder: her galeri gorseli
    ya sec_gorseller/elenen ya da denetlenmedi altinda gorunur (union == tum galeri).

    Iki denetim-disi kaynagi kapsar:
      1. cap ustu (emekli motor'e HIC gonderilmedi)  -> neden "kota ust siniri (denetlenmedi)"
      2. gonderildi ama emekli motor ne secti ne eledi -> neden "emekli motor kapsamadi (denetlenmedi)"
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
            denetlenmedi.append({"dosya": f, "neden": "emekli motor kapsamadi (denetlenmedi)"})
    out["denetlenmedi"] = denetlenmedi
    return out


def emekli_motor_cagir(prompt, imgler, cikti_yolu):
    """emekli motor exec calistir; son mesaji cikti_yolu'na SAF JSON olarak yazar."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as sf:
        json.dump(SEMA, sf)
        sema_yolu = sf.name
    cmd = [EMEKLI_MOTOR_IKILI, "exec",
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
    ok, hata = emekli_motor_cagir(prompt, [os.path.join(d, f) for f in imgs], onerip)
    if not ok:
        print("=== %s === emekli motor basarisiz: %s" % (tid, hata))
        return
    try:
        out = json.load(open(onerip))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print("=== %s === emekli motor gecersiz JSON dondu: %s" % (tid, e))
        if os.path.exists(onerip):
            os.unlink(onerip)   # bozuk dosya birakma — cagiran "oneri var" saniyor
        return

    # KATEGORI NORMALIZASYONU (sessiz-hata kapisi): oneri.json'u TUM ekle scriptleri
    # (urun-ekle / printables-ekle / makerworld-ekle / mmf / cgt / cults3d) okur ve degeri
    # urunler.json'a AYNEN yazar. Kanonik olmayan ad urunu kategoriden gorunmez yapar.
    ham_kat = out.get("kategori")
    kanonik = kanonik_kategori(ham_kat)
    if kanonik is None:
        print("=== %s === emekli motor gecersiz kategori dondu: %r (gecerli: %s)"
              % (tid, ham_kat, ", ".join(KATEGORILER)))
        os.unlink(onerip)       # fail-closed: kotu kategoriyle urun STAGE ETME
        return
    if kanonik != ham_kat:
        print("=== %s === kategori normalize edildi: %r -> %r" % (tid, ham_kat, kanonik))
        out["kategori"] = kanonik

    # DENETIM KAPSAMI (sessiz g5+ kapisi): TUM galeriye karsi kapsam hesapla; denetlenmeyen
    # (cap ustu ya da emekli motor'in kapsamadigi) gorselleri "denetlenmedi" ile ISARETLE. oneri.json'u
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
        sys.exit("KREDI KAPISI: urun-basi emekli motor cagrisi kapali. Yalniz Okan acikca izin verirse "
                 "PRUVO_URUN_AI_IZNI=EVET kullanilir.")
    if not os.path.exists(EMEKLI_MOTOR_IKILI):
        sys.exit("emekli motor bulunamadi: %s (ChatGPT.app kurulu mu?)" % EMEKLI_MOTOR_IKILI)
    for tid in sys.argv[1:]:
        process(tid)


if __name__ == "__main__":
    main()
