#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Üyelik ürünlerini toplu listeleme / kaldırma güvenlik betiği.

Üyelik tedarikçilerinin modelleri YALNIZCA aylık üyelik aktifken satılabilir.
Üyelik biterse bu ürünler siteden çekilmelidir (lisans ihlali olmasın).

Üyelik bilgisi PUBLIC urunler.json'da DEĞİL, gizli .urun-kaynaklari.json'dadır
(her ürün kaydında "uyelik" anahtarı — ticari mahremiyet, 2026-07-15 taşındı).
Bu betik oradan bulur; istenirse ürünleri tools/duzelt.py --sil ile kaldırır
(guard'ın meşru yolu) ve R2'deki görsellerini siler.

🔴 R2 SİLME ARTIK KALDIRMAYI DURDURAMAZ (30 Tem 2026, K1):
Görsel kovasında Bucket Lock + retention penceresi var → kova FİİLEN append-only:
silme ve aynı anahtara yazma `HTTP 409 ObjectLockedByBucketPolicy` ile REDDEDİLİYOR.
Eskiden `sil_ve_dogrula` çağrısı try/except DIŞINDAydı ve `duzelt.py --sil` adımı bu
döngüden SONRA geliyordu → ilk 409'da betik patlıyor, ürün siteden HİÇ kalkmıyordu
(lisansı biten ürün canlıda kalır = ticari/hukuki risk). Artık:
  * her R2 silme hatası (409 dahil, YALNIZ 409 değil) yakalanır, GÜRÜLTÜLÜ basılır,
    anahtar kalıcı "silinecekler kuyruğuna" (.r2-silme-kuyrugu.json) yazılır,
  * döngü devam eder ve `duzelt.py --sil` adımına MUTLAKA ulaşılır → ürün siteden
    (ve pre-push senkronuyla D1'den) kalkar.
Retention dolunca kuyruk süpürülür: `--kuyruk-supur --uygula` (K2).

⚠️ tools/r2-upload.py `sil_ve_dogrula()` DEĞİŞTİRİLMEDİ — o fail-closed ve gürültülü
patlaması DOĞRU davranış; onarım onu ÇAĞIRAN yerdedir (ikinci kopya AÇILMAZ).

Kullanım:
    python3 tools/uyelik-cek.py                     # sadece LİSTELE (dry-run, güvenli)
    python3 tools/uyelik-cek.py --uygula            # urunler.json'dan KALDIR
    python3 tools/uyelik-cek.py --uygula --r2       # ayrıca R2 görsellerini de sil
    python3 tools/uyelik-cek.py --etiket <ad>       # sadece belirli üyeliği hedefle
    python3 tools/uyelik-cek.py --kuyruk-supur      # silme kuyruğunu LİSTELE (ağsız)
    python3 tools/uyelik-cek.py --kuyruk-supur --uygula   # kuyruğu R2'de silmeyi DENE

Kaldırdıktan sonra: git add urunler.json && commit && push (CI sayfaları yeniden üretir).
NOT: Ücretsiz gear generator üyelik biterse CC BY'a döner — istersen onu kaldırmak yerine
`lisans` alanını geri koyup (atıflı) tutabilirsin.
"""
import os, sys, json, subprocess, importlib.util, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")
KAYNAK_PATH = os.path.join(ROOT, ".urun-kaynaklari.json")
DUZELT = os.path.join(ROOT, "tools", "duzelt.py")
R2_MOD_PATH = os.path.join(ROOT, "tools", "r2-upload.py")
# Silinemeyen R2 anahtarlarının kalıcı kuyruğu (yerel durum, gitignore'da).
KUYRUK_PATH = os.path.join(ROOT, ".r2-silme-kuyrugu.json")

# K4 — Bucket Lock yüzünden ŞİMDİ silinemeyen denetim artıkları. Kuyruk dosyası
# gitignore'lu YEREL durumdur (worktree/klon değişince kaybolur) → bu iki anahtar
# İZLENEN kodda taşınır ve her süpürmede kuyruğa harmanlanır. Silindikten sonra
# sonda "zaten-yoktu" der (sil() çağrılmaz), yani yeniden harmanlama zararsızdır.
DENETIM_ARTIKLARI = [
    ("urunler/lock-sonda-30tem-88930b3b.jpg", "30 Tem lock sondasi artigi (Bucket Lock)"),
    ("denetim/lock-kapsam-sonda-30tem-7c98a1db.jpg", "30 Tem lock kapsam sondasi artigi (Bucket Lock)"),
]


def _r2_modul():
    """tools/r2-upload.py'yi yükle (ad tirelidir, düz import edilemez).
    R5 silme kapısının TEK kopyası orada; burada ikinci kopya AÇILMAZ."""
    spec = importlib.util.spec_from_file_location("r2_upload_mod", R2_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- silinecekler kuyruğu -----------------------------------------------------
def kuyruk_oku(yol=None):
    """Kuyruğu okur. Dosya yoksa/bozuksa BOŞ liste (kuyruk okuma kaldırmayı durduramaz)."""
    yol = yol or KUYRUK_PATH
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (IOError, OSError, ValueError):
        return []
    return veri if isinstance(veri, list) else []


def kuyruk_yaz(kayitlar, yol=None):
    """Atomik yaz (tmp + os.replace) — yarıda kesilen yazma kuyruğu çöpe çevirmesin."""
    yol = yol or KUYRUK_PATH
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, yol)


def kuyruga_ekle(anahtar, sebep, urun=None, yol=None, simdi=None):
    """Anahtarı kuyruğa yaz (anahtara göre tekilleştirilmiş; sebep/deneme güncellenir).

    Kuyruk yazımının KENDİSİ de kaldırmayı durdurmamalı → her hata yutulur ama
    GÜRÜLTÜLÜ basılır (fail-open BİLİNÇLİ: buradaki hata ürünü canlıda tutamaz)."""
    zaman = simdi or datetime.datetime.now().isoformat(timespec="seconds")
    try:
        kayitlar = kuyruk_oku(yol)
        for k in kayitlar:
            if k.get("anahtar") == anahtar:
                k["sebep"] = sebep
                k["son_deneme"] = zaman
                k["deneme"] = int(k.get("deneme", 1)) + 1
                if urun and not k.get("urun"):
                    k["urun"] = urun
                break
        else:
            kayitlar.append({"anahtar": anahtar, "sebep": sebep, "urun": urun,
                             "eklendi": zaman, "son_deneme": zaman, "deneme": 1})
        kuyruk_yaz(kayitlar, yol)
        return True
    except Exception as exc:                                   # pragma: no cover - IO
        print("  UYARI: kuyruga YAZILAMADI (%s): %s — anahtar: %s"
              % (type(exc).__name__, exc, anahtar))
        return False


def kuyruktan_dus(anahtar, yol=None):
    kayitlar = [k for k in kuyruk_oku(yol) if k.get("anahtar") != anahtar]
    kuyruk_yaz(kayitlar, yol)


def denetim_artiklarini_harmanla(yol=None, simdi=None):
    """K4: izlenen DENETIM_ARTIKLARI listesini kuyruğa ekler (idempotent)."""
    mevcut = {k.get("anahtar") for k in kuyruk_oku(yol)}
    eklendi = 0
    for anahtar, sebep in DENETIM_ARTIKLARI:
        if anahtar not in mevcut:
            if kuyruga_ekle(anahtar, sebep, urun=None, yol=yol, simdi=simdi):
                eklendi += 1
    return eklendi


# --- asıl kaldırma akışı ------------------------------------------------------
def r2_gorselleri_sil(hedef, base, sil_ve_dogrula, kuyruk_yolu=None, yaz=print):
    """Hedef ürünlerin R2 görsellerini silmeyi DENER. ASLA RAISE ETMEZ.

    `sil_ve_dogrula(key)` -> "silindi-dogrulandi" | "zaten-yoktu"; hata fırlatabilir
    (409 ObjectLockedByBucketPolicy, R5 red, yetki, ağ...). HER hata yakalanır,
    anahtar kuyruğa yazılır ve döngü DEVAM eder → çağıran `duzelt.py --sil` adımına
    her koşulda ulaşır. Dönüş: (basarili_anahtarlar, kuyruga_alinanlar).
    """
    basarili, kuyruga = [], []
    for o in hedef:
        for url in o.get("gorseller", []):
            if not url.startswith(base):
                continue
            key = url[len(base):]
            try:
                sonuc = sil_ve_dogrula(key)
            except Exception as exc:
                sebep = "%s: %s" % (type(exc).__name__, exc)
                yaz("  R2 SİLİNEMEDİ (kuyruga alindi): %s — sebep: %s" % (key, sebep))
                kuyruga_ekle(key, sebep, urun=o.get("id"), yol=kuyruk_yolu)
                kuyruga.append(key)
                continue
            yaz("  R2 %s: %s" % (sonuc, key))
            basarili.append(key)
    return basarili, kuyruga


def urunleri_kaldir(hedef, kaldir, yaz=print):
    """Her ürünü urunler.json'dan kaldırır. Bir ürünün hatası DİĞERLERİNİ durdurmaz."""
    kaldirilan, basarisiz = [], []
    for o in hedef:
        try:
            kaldir(o["id"])
        except Exception as exc:
            yaz("  KALDIRILAMADI: %s — %s: %s" % (o["id"], type(exc).__name__, exc))
            basarisiz.append(o["id"])
            continue
        kaldirilan.append(o["id"])
    return kaldirilan, basarisiz


def kaldirma_akisi(hedef, kaldir, base=None, sil_ve_dogrula=None,
                   kuyruk_yolu=None, yaz=print):
    """K1 sözleşmesi: R2 silme SONUCU NE OLURSA OLSUN ürün kaldırma adımı KOŞAR.

    Dönüş: {"r2_basarili", "r2_kuyruk", "kaldirilan", "kaldirilamayan"}.
    """
    r2_basarili, r2_kuyruk = [], []
    if sil_ve_dogrula is not None:
        try:
            r2_basarili, r2_kuyruk = r2_gorselleri_sil(
                hedef, base, sil_ve_dogrula, kuyruk_yolu=kuyruk_yolu, yaz=yaz)
        except Exception as exc:
            # R2 katmanının TAMAMI çökse bile (istemci kurulumu, beklenmedik hata)
            # kaldırma devam eder — ürünün canlıda kalması daha büyük risk.
            yaz("  UYARI: R2 silme katmani coktu (%s: %s) — kaldirmaya DEVAM"
                % (type(exc).__name__, exc))
    kaldirilan, kaldirilamayan = urunleri_kaldir(hedef, kaldir, yaz=yaz)
    if r2_kuyruk:
        yaz("")
        yaz("🔴 %d gorsel R2'den SILINEMEDI, kuyruga alindi (%s):"
            % (len(r2_kuyruk), kuyruk_yolu or KUYRUK_PATH))
        for k in r2_kuyruk:
            yaz("   - " + k)
        yaz("   Retention dolunca: python3 tools/uyelik-cek.py --kuyruk-supur --uygula")
    return {"r2_basarili": r2_basarili, "r2_kuyruk": r2_kuyruk,
            "kaldirilan": kaldirilan, "kaldirilamayan": kaldirilamayan}


def kuyruk_supur(sil_ve_dogrula, kuyruk_yolu=None, yaz=print):
    """K2: kuyruktaki anahtarları silmeyi dener. Silinen düşer, silinemeyen SEBEBİYLE kalır.

    ASLA RAISE ETMEZ; dönüş: (dusenler, kalanlar)."""
    denetim_artiklarini_harmanla(yol=kuyruk_yolu)
    kayitlar = kuyruk_oku(kuyruk_yolu)
    dusen, kalan = [], []
    for k in kayitlar:
        anahtar = k.get("anahtar")
        if not anahtar:
            continue
        try:
            sonuc = sil_ve_dogrula(anahtar)
        except Exception as exc:
            sebep = "%s: %s" % (type(exc).__name__, exc)
            yaz("  HALA SILINEMIYOR: %s — %s" % (anahtar, sebep))
            k["sebep"] = sebep
            k["son_deneme"] = datetime.datetime.now().isoformat(timespec="seconds")
            k["deneme"] = int(k.get("deneme", 1)) + 1
            kalan.append(k)
            continue
        yaz("  %s: %s" % (sonuc, anahtar))
        dusen.append(anahtar)
    kuyruk_yaz(kalan, kuyruk_yolu)
    return dusen, kalan


# --- R2 bağlantısı (yalnız gerçek koşumda) ------------------------------------
def _r2_sonda():
    """(sil_ve_dogrula, base) döndürür. Kimlik dosyası OKUNUR ama ASLA BASILMAZ."""
    import boto3
    cfg = json.load(open(os.path.join(ROOT, ".r2-credentials.json")))
    s3 = boto3.client("s3", endpoint_url=cfg["endpoint"],
                      aws_access_key_id=cfg["access_key"],
                      aws_secret_access_key=cfg["secret"], region_name="auto")
    # R5 (30 Tem 2026): silme çağrısının kendi başarısı KANIT DEĞİL — silme sonrası
    # BAĞIMSIZ varlık kontrolü yapılır, nesne hâlâ görünüyorsa RAISE (fail-closed).
    r2mod = _r2_modul()
    var_mi = r2mod.s3_var_mi(s3, cfg["bucket"])
    sil = lambda k: s3.delete_object(Bucket=cfg["bucket"], Key=k)
    return (lambda key: r2mod.sil_ve_dogrula(key, var_mi, sil)), cfg["public_base"] + "/"


def _duzelt_kaldir(urun_id):
    # duzelt.py --sil = guard'in mesru silme yolu (dogrudan json.dump guard'ca geri alinir)
    subprocess.run([sys.executable, DUZELT, urun_id, "--sil", "uyelik bitti"], check=True)


def _kuyruk_kipi(args):
    """--kuyruk-supur: --uygula yoksa AĞSIZ listeleme, varsa gerçek silme denemesi."""
    denetim_artiklarini_harmanla()
    kayitlar = kuyruk_oku()
    if not kayitlar:
        print("Silme kuyrugu bos.")
        return 0
    print("Silme kuyrugunda %d anahtar (%s):" % (len(kayitlar), KUYRUK_PATH))
    for k in kayitlar:
        print("  - %s  [deneme=%s]  sebep: %s"
              % (k.get("anahtar"), k.get("deneme"), k.get("sebep")))
    if "--uygula" not in args:
        print("\n(dry-run) Denemek icin: python3 tools/uyelik-cek.py --kuyruk-supur --uygula")
        return 0
    sil_ve_dogrula, _base = _r2_sonda()
    dusen, kalan = kuyruk_supur(sil_ve_dogrula)
    print("\n%d anahtar kuyruktan dustu, %d anahtar KALDI." % (len(dusen), len(kalan)))
    return 0


def main():
    args = sys.argv[1:]
    if "--kuyruk-supur" in args:
        sys.exit(_kuyruk_kipi(args))
    uygula = "--uygula" in args
    r2 = "--r2" in args
    etiket = None
    if "--etiket" in args:
        etiket = args[args.index("--etiket") + 1]

    data = json.load(open(JSON_PATH, encoding="utf-8"))
    kaynak = json.load(open(KAYNAK_PATH, encoding="utf-8"))
    uyelik_by_id = {uid: e.get("uyelik") for uid, e in kaynak.items()
                    if isinstance(e, dict) and e.get("uyelik")}
    hedef = [o for o in data
             if o.get("id") in uyelik_by_id
             and (etiket is None or uyelik_by_id[o["id"]] == etiket)]

    if not hedef:
        print("Üyelik etiketli ürün yok.")
        return

    print("Üyelik etiketli %d ürün:" % len(hedef))
    for o in hedef:
        print("  - %s  [uyelik=%s]  %s" % (o["id"], uyelik_by_id[o["id"]], o.get("baslik", "")))

    if not uygula:
        print("\n(dry-run) Kaldırmak için: python3 tools/uyelik-cek.py --uygula [--r2]")
        return

    sil_ve_dogrula, base = (None, None)
    if r2:
        sil_ve_dogrula, base = _r2_sonda()

    sonuc = kaldirma_akisi(hedef, _duzelt_kaldir, base=base,
                           sil_ve_dogrula=sil_ve_dogrula)

    print("\n%d ürün urunler.json'dan kaldırıldı." % len(sonuc["kaldirilan"]))
    if sonuc["kaldirilamayan"]:
        print("🔴 %d ürün KALDIRILAMADI: %s — TEKRAR KOŞTUR (canlida duruyorlar)"
              % (len(sonuc["kaldirilamayan"]), ", ".join(sonuc["kaldirilamayan"])))
    print("Şimdi: git add urunler.json && commit && push")
    if sonuc["kaldirilamayan"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
