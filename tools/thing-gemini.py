#!/usr/bin/env python3
"""Gemini YARDIMCISI — pahali bilissel adimlari (gorsel secme + Turkce icerik) devreder.

Amac: token diyeti. Gorsel okuma + aciklama yazma Claude'un baglamina GIRMEZ; Gemini yapar,
temiz JSON doner, Claude sadece kucuk metni okur.

Kullanim:  python3 tools/thing-gemini.py <thing_id> [<thing_id> ...]
Onkosul :  once  python3 tools/thing-hazirla.py <id...>  (gorselleri + meta.json'u uretir)

Her id icin `.thing-cache/<id>/meta.json` + `gN.jpg`'leri okur, Gemini'ye yollar, sunu doner:
  { sec_gorseller, elenen, baslik, aciklama, kategori, marka, not }
Ciktiyi ekrana + `.thing-cache/<id>/oneri.json`'a yazar.

Anahtar: `.gemini-key` (gitignore). 1. satir = API key. Istege bagli 2. satir = model adi.
Ucretsiz key:  https://aistudio.google.com/apikey   (Google hesabiyla, "Create API key").
Sir icermez; harici pip paketi YOK (duz REST).
"""
import base64, json, os, sys, time, urllib.request, urllib.error

ROOT = "/Users/okan/dev/pruvo"
IMGROOT = os.path.join(ROOT, ".thing-cache")
KEYFILE = os.path.join(ROOT, ".gemini-key")
DEFAULT_MODEL = "gemini-flash-latest"   # ucretsiz kota burada (2.0-flash 429 verir; 2.5 yeni kullaniciya kapali)
FALLBACK_MODEL = "gemini-flash-lite-latest"   # ana model 503/yogun ise buna dus
RETRYABLE = (429, 500, 503)

KATEGORILER = ["Tamirat", "Marin", "Otomobil", "Motosiklet", "Bisiklet", "Ev",
               "Ofis", "Elektronik", "Kamera", "Bahce", "Dekorasyon", "Oyun/Hobi"]

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
- sec_gorseller: dosya adlari (or. "g1.jpg"), EN IYI ilk sirada. elenen: {dosya, neden} (neden 1-2 kelime).

--- GOREV 2: TURKCE ICERIK ---
- baslik: kisa, net Turkce. Parca adi + varsa marka/model. Abartma yok.
- aciklama: ferah, TARANABILIR. Kisa 1-2 cumle giris + ardindan '\\n' ile ayrilmis kisa maddeler
  (ne ise yarar, nasil kullanilir, montaj). Gorsel/basliktan EMIN OLMADIGIN ozelligi UYDURMA.
  Olcu verildiyse aciklamanin SONUNA aynen su satiri (DUZGUN TURKCE, diakritikli) ekle:
  "Yaklasik dis olculer: A × B × C mm." -> yani cikti "Yaklaşık dış ölçüler: A × B × C mm."
  seklinde olmali (A × B × C degerlerini verilen olcuyle doldur, × isaretini kullan). "3D baski" deme.
- kategori: SADECE su 12'den biri: %s
  Secim kurali (urunun ait oldugu alan / calisma prensibi):
  * Arac/marka-OZEL parca -> ilgili arac kategorisine (Otomobil/Motosiklet/Bisiklet/Marin), Tamirat'a DEGIL.
  * Tamirat: marka-BAGIMSIZ genel tamir/atolye aleti (mengene, kelepce, klips, tirtikli civata vb.).
  * Kamera: kameraya dair HER sey (GoPro/aksiyon kamera, montaj, tripod, lens aksesuari) -> Elektronik'e degil.
  * Elektronik: elektrik/pille calisan cihaz parcasi (kahve makinesi, buzdolabi, supurge, 3D yazici) -
    kamera HARIC, e-bike HARIC.
  * Bisiklet: bisiklet + e-bike parcalari (e-bike Elektronik'e DEGIL).
  * Ev: elektriksiz ev esyasi. Ofis: ofis/kirtasiye. Bahce: bahce/guc ekipmani. Dekorasyon: sus.
    Oyun/Hobi: oyuncak/hobi/koleksiyon. Marin: tekne/denizcilik.
- marka: DIZI. Basliktaki/urundeki marka veya model adlari (or. ["Audi","Volkswagen"]). Jenerik urunse [].

--- KAYNAK BILGISI ---
Kaynak baslik: %s
Tasarimci   : %s
Lisans      : %s
Olcu (mm)   : %s

CIKTI: SADECE su semada gecerli JSON dondur (markdown/backtick YOK):
{"sec_gorseller":["g1.jpg"],"elenen":[{"dosya":"g2.jpg","neden":"logo"}],
 "baslik":"...","aciklama":"...","kategori":"Otomobil","marka":["..."],"not":"kisa gerekce"}
"""


def load_key():
    if not os.path.exists(KEYFILE):
        sys.exit("HATA: .gemini-key yok. Ucretsiz anahtar: https://aistudio.google.com/apikey\n"
                 "Sonra:  1. satira API key yaz  ->  " + KEYFILE)
    lines = [x.strip() for x in open(KEYFILE).read().splitlines() if x.strip()]
    key = lines[0]
    model = lines[1] if len(lines) > 1 else os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    return key, model


def _one_call(key, model, body):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
           % (model, key))
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    resp = json.loads(raw)
    return resp["candidates"][0]["content"]["parts"][0]["text"]


def gemini(key, model, parts):
    """Ana model + yedek model; her birinde 429/500/503'te artan bekleyisle 3 deneme."""
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4,
                             "maxOutputTokens": 2048,
                             # 3.x flash'ta "thinking" varsayilan acik -> dusunme token'lari cikti
                             # butcesini yiyip JSON'u yarida kesiyor. Kapat (bu is icin gereksiz).
                             "thinkingConfig": {"thinkingBudget": 0}},
    }).encode("utf-8")
    last = ""
    for m in [model, FALLBACK_MODEL]:
        if m == FALLBACK_MODEL and model == FALLBACK_MODEL:
            continue
        for attempt in range(3):
            try:
                return _one_call(key, m, body)
            except urllib.error.HTTPError as e:
                last = "HTTP %s (%s): %s" % (e.code, m, e.read().decode("utf-8", "ignore")[:200])
                if e.code in RETRYABLE and attempt < 2:
                    time.sleep(3 * (attempt + 1)); continue
                break   # kalici hata (or. 400/403/404) -> sonraki modele gec
            except (KeyError, IndexError) as e:
                last = "beklenmedik yanit (%s): %s" % (m, e); break
            except Exception as e:
                last = "%s (%s)" % (e, m)
                if attempt < 2:
                    time.sleep(3 * (attempt + 1)); continue
                break
    sys.exit("Gemini basarisiz (ana+yedek denendi): " + last)


def process(tid, key, model):
    d = os.path.join(IMGROOT, tid)
    mp = os.path.join(d, "meta.json")
    if not os.path.exists(mp):
        print("=== %s === ATLA: meta.json yok (once thing-hazirla.py calistir)" % tid)
        return
    meta = json.load(open(mp))
    imgs = sorted([f for f in os.listdir(d) if f.startswith("g") and f.endswith(".jpg")])
    if not imgs:
        print("=== %s === ATLA: gorsel yok" % tid)
        return
    olcu = meta.get("olcu_mm")
    olcu_s = ("%d x %d x %d" % tuple(olcu)) if olcu else "yok"
    parts = [{"text": PROMPT % (", ".join(KATEGORILER), meta.get("baslik", "?"),
                                meta.get("tasarimci", "?"), meta.get("lisans", "?"), olcu_s)}]
    for f in imgs:
        b = base64.b64encode(open(os.path.join(d, f), "rb").read()).decode()
        parts.append({"text": "GORSEL: " + f})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b}})
    txt = gemini(key, model, parts)
    try:
        out = json.loads(txt)
    except json.JSONDecodeError:
        print("=== %s === Gemini gecersiz JSON dondu:\n%s" % (tid, txt[:600]))
        return
    json.dump(out, open(os.path.join(d, "oneri.json"), "w"), ensure_ascii=False, indent=2)
    print("=== thing:%s === (oneri -> %s/oneri.json)" % (tid, d))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    # secilen gorsellerin TAM yollari (r2-upload icin)
    print("   SECILEN yollar:")
    for f in out.get("sec_gorseller", []):
        print("      ", os.path.join(d, f))
    print()


def main(ids):
    key, model = load_key()
    print("[gemini modeli: %s]" % model)
    for tid in ids:
        process(tid, key, model)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/thing-gemini.py <thing_id> [<thing_id> ...]")
    main(sys.argv[1:])
