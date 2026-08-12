#!/usr/bin/env python3
"""MakerWorld'te MARKA/terim arar; sitede OLMAYAN + satilabilir + gurultusuz + MARKA-ALAKALI
model ID'lerini verir. Printables'teki printables-ara.py'nin MakerWorld esdegeri.

Kullanim:  python3 tools/makerworld-ara.py "Renault" [max]
   -> aday model ID'lerini bir satirda (bosluk ayirli) yazar + id/lisans/baslik listesi basar.

ELER:  * satilamaz lisans (satilabilir() FAIL-CLOSED — Standard/Exclusive/NC/bilinmeyen)
       * anahtarlik/logo/amblem/minyatur/kit-card gurultusu (COP listesi)
       * \\bMARKA\\b KELIME-SINIRI: marka adi baslik/etiket/slug'da TAM KELIME olarak gecmiyorsa
         ele (Oxford/afford gibi alt-dize gurultusu elensin; Turkce-duyarli). Mimar bu inline
         filtreyi ORTAK filtreyle sonra birlestirecek (bkz. paket).
       * `.urun-kaynaklari.json`'da zaten kayitli MakerWorld model ID'leri (dedup)

Token GEREKMEZ (MakerWorld public API). Sir icermez.
"""
import importlib.util, os, re, sys

# VERI KOKU: `.urun-kaynaklari.json` DAIMA ANA kopyada durur, ama kok SABIT YAZILMAZ —
# sabit "<gelistirici-evi>/depo" CI kosucusunda YOKTUR (7 Agu 2026: ayni desen serit-a3'u
# kirmizi yakip yayini 4+ saat kapatti; yerelde HIC kirmizi yanmaz). veri_kok git'e sorar:
# worktree'de ANA kopyayi, temiz klonda/CI'da klonun kokunu dondurur.
_KENDI_DIZIN = os.path.dirname(os.path.abspath(__file__))
_vkspec = importlib.util.spec_from_file_location("veri_kok",
                                                os.path.join(_KENDI_DIZIN, "veri_kok.py"))
_vk = importlib.util.module_from_spec(_vkspec); _vkspec.loader.exec_module(_vk)
_KOD_KOK, ROOT, _KOK_UYARI = _vk.cozumle(__file__)
if _KOK_UYARI:
    sys.stderr.write(_KOK_UYARI)
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

# MakerWorld API'sinin ticari kullanima acik dort lisans havuzu. Her biri ayri sorgulanir.
SATILABILIR_LISANSLAR = ("CC0", "BY", "BY-SA", "BY-ND")

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("makerworld_api", os.path.join(_HERE, "makerworld-api.py"))
mw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mw)


# --- \bMARKA\b kelime-siniri (Turkce-duyarli) ---
_KELIME = "a-z0-9çğıöşü"

# Buyuk/kucuk KATLAMA kurali TEK KAYNAK: printables-api.marka_katlamalari().
# Kendi _tr_lower kopyasi vardi ve TUMU-BUYUK latin marka adini kaciriyordu
# ('NISSAN' -> 'nıssan' != 'nissan'); kusur ILK KEZ Nissan x MakerWorld hasadinda
# goruldu (2026-08-04). Kelime-siniri regex'i (yukaridaki _KELIME sinifi) DEGISMEDI.
_pr_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(_HERE, "printables-api.py"))
_pr = importlib.util.module_from_spec(_pr_spec)
_pr_spec.loader.exec_module(_pr)


# 🔴 COK KELIMELI MARKA KORLUGU (K63, olculdu 12 Agu 2026)
# Marka terimi ONCE tek parca olarak derleniyordu (`re.escape(m)`), yani "alfa romeo"
# YALNIZ tek bosluklu yazimla eslesiyordu. Marka adi iki kelimeliyse platformdaki
# YAYGIN yazimlar (AlfaRomeo · Alfa-Romeo · alfa_romeo · Mercedes Benz <-> Mercedes-Benz)
# TAM KELIME sayilmayip `elenen_marka` kovasina dusuyordu. Etkilenen markalar:
# Land Rover · Aston Martin · Mercedes-Benz · Alfa Romeo.
# COZUM MARKA-BAGIMSIZDIR (marka basina istisna listesi YASAK — elle tutulan liste her
# partide bayatlar): marka adi AYRAC'lardan bolunur, parcalar arasinda ayrac SERBEST
# birakilir. Tek kelimeli markada desen BIREBIR eskisidir (davranis degismez).
#
# ⚠️ NE KADAR GENISLETILDIGI OLCULDU (canli MakerWorld, 4 marka, 584 kayit):
#     terim          donen  ESKI gecen  YENI gecen  KURTARILAN
#     alfa romeo      143       23          26          +3   (ör. `AFGiuliaFull`)
#     land rover      155       33          40          +7   (ör. `Landrover D90`)
#     aston martin    151       24          25          +1
#     mercedes benz   135       47          55          +8
#     ford (tek kel.) 308      294         294           0   <- tek kelime SABIT
# 🔴 DAHA GENISI OLCULDU ve REDDEDILDI: "cok kelimeli terimde marka filtresini hic
#    uygulama, API alakasina guven" dendiginde alfa romeo sorgusunun 143 sonucunun
#    118'i (%82,5) HICBIR marka kelimesi tasimiyordu (Citroën Berlingo, Skoda Octavia,
#    Bugatti, JEEP...). Yani MakerWorld sorgusu bulanik; genisleme oraya kadar acilamaz.
#    ⚠️ KALAN SINIR (kapanmadi, kapanamaz): yalniz MODEL adi tasiyan baslik
#    ("Giulia grill keychain") hicbir metin kuralinin yakalayamayacagi sinifta kalir —
#    marka dizesi metinde YOKTUR. O sinifin telafisi MODEL TERIMLI yeniden taramadir;
#    bu yuzden `elenen_marka` kovasi "gorulen" SAYILMAZ (asagidaki kova taksonomisi).
_MARKA_AYRAC = r"[\s\-_.·]"


def _marka_deseni(m):
    """Katlanmis marka adi -> derlenmis kelime-sinirli desen (ayraclara duyarsiz)."""
    parcalar = [re.escape(p) for p in re.split(_MARKA_AYRAC + "+", m) if p]
    if not parcalar:
        return None
    govde = (_MARKA_AYRAC + "*").join(parcalar)
    return re.compile(r"(?<![%s])%s(?![%s])" % (_KELIME, govde, _KELIME))


def marka_geciyor(marka, *metinler):
    """marka, verilen metinlerden en az birinde TAM KELIME olarak geciyor mu?
    'ford' -> 'Ford Mustang' EVET; 'Oxford'/'afford' HAYIR (alt-dize).
    'nissan' -> 'NISSAN GTR' EVET (latin katlama; bkz. printables-api.marka_katlamalari).
    'alfa romeo' -> 'AlfaRomeo Giulia' / 'Alfa-Romeo 156' EVET (ayrac serbest),
                    'Romeo and Juliet' / 'Alfa Laval' HAYIR (kelimeler bitisik degil)."""
    if not (marka or "").strip():
        return False
    for m, katla in _pr.marka_katlamalari(marka):
        if not m:
            continue
        pat = _marka_deseni(m)
        if pat is None:
            continue
        if any(pat.search(katla(t or "")) for t in metinler):
            return True
    return False


# --- KESIF KOVA TAKSONOMISI: hangi kova "GORULDU, HUKUM VERILDI" sayilir? ------------
# 🔴 K63 IKINCI KUSUR (olculdu): ek-terim/model-terim taramalari kanonik "gorulen" ID
# kumesine `elenen_marka` kovasini da katiyordu. Ama o kova "bu ID kotu" demez, yalnizca
# "BU TERIM metinde gecmiyor" der — BASKA bir terim (model adi) icin hukum DEGILDIR.
# Gorulen sayilinca model-terimli telafi taramasi tam da kurtarmasi gereken kayitlari
# atliyordu, yani birinci kusurun telafisi CALISMIYORDU.
# Bu taksonomi TEK KAYNAKTIR: tarama havuzunu okuyan her arac gorulen_idler()'i cagirir,
# kendi kova listesini TUTMAZ (ikiz tanim sessizce ayrisir).
HUKUMLU_KOVALAR = ("adaylar", "elenen_cop", "elenen_nc", "zaten_ekli")
KARARSIZ_KOVALAR = ("elenen_marka",)
TUM_KOVALAR = HUKUMLU_KOVALAR + KARARSIZ_KOVALAR


class BilinmeyenKova(RuntimeError):
    pass


def _kova_idleri(deger):
    ids = set()
    for x in (deger or []):
        if isinstance(x, (list, tuple)):
            ids.add(str(x[0]))
        elif isinstance(x, dict):
            ids.add(str(x.get("id")))
        else:
            ids.add(str(x))
    return ids


def gorulen_idler(havuz):
    """Havuzdaki HUKUM VERILMIS ID'ler — yeniden taranmasa bilgi kaybi OLMAZ.

    `elenen_marka` BILEREK DISARIDADIR (bkz. taksonomi notu). Havuzda taniinmayan bir
    kova varsa FAIL-CLOSED: yeni bir kova sessizce 'gorulen' ya da 'kararsiz' sayilamaz."""
    if not isinstance(havuz, dict):
        raise BilinmeyenKova("havuz sozluk olmali, %r geldi" % type(havuz))
    bilinmeyen = [k for k in havuz if k not in TUM_KOVALAR]
    if bilinmeyen:
        raise BilinmeyenKova(
            "taniinmayan kova(lar): %s -> HUKUMLU_KOVALAR/KARARSIZ_KOVALAR'da sinifla"
            % ", ".join(sorted(bilinmeyen)))
    ids = set()
    for kova in HUKUMLU_KOVALAR:
        ids |= _kova_idleri(havuz.get(kova))
    return ids


def kararsiz_idler(havuz):
    """Hukum VERILMEMIS ID'ler — MODEL/ek terimle YENIDEN taranmali."""
    if not isinstance(havuz, dict):
        raise BilinmeyenKova("havuz sozluk olmali, %r geldi" % type(havuz))
    bilinmeyen = [k for k in havuz if k not in TUM_KOVALAR]
    if bilinmeyen:
        raise BilinmeyenKova("taniinmayan kova(lar): %s" % ", ".join(sorted(bilinmeyen)))
    ids = set()
    for kova in KARARSIZ_KOVALAR:
        ids |= _kova_idleri(havuz.get(kova))
    return ids


def mevcut_idler():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'makerworld\.com/(?:[a-z]{2}/)?models/(\d+)', blob):
            ids.add(m)
        for m in re.findall(r'makerworld[:/](\d{3,})', blob):
            ids.add(m)
    return ids


def main(term, maxn, derin=False, cikis_limiti=None):
    """term/marka ara, sitede OLMAYAN uygun aday model ID'lerini bas.

    Sayfalama (pagination) ile keeper-cap AYRI (2026-07-18 duzeltme; thing-ara.py deseni):
      - derin=False (varsayilan, GERIYE-UYUMLU): dongu `maxn` keeper toplayinca DURUR (eski davranis).
      - derin=True (--derin): `maxn` dongoyu DURDURMAZ; ham havuz IKINCIL tavana (offset<3000) ya da
        `total` tukenene kadar TAM taranir. Boylece uygun havuz erken kesilmez.
    `cikis_limiti` (opsiyonel): siralamadan sonra cikti listesini kirpar (None=kirpma yok)."""
    mevcut = mevcut_idler()
    bulunan, elenen_cop, elenen_nc, elenen_marka = [], [], [], []
    seen = set()
    offset, total = 0, None
    toplam_eslesme = 0
    lisans_indeksi = 0
    lisans_bulunan = 0
    LIMIT = 40
    while lisans_indeksi < len(SATILABILIR_LISANSLAR):
        if offset >= 3000:
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        arama_lisansi = SATILABILIR_LISANSLAR[lisans_indeksi]
        try:
            res = mw.search(term, limit=LIMIT, offset=offset, licenses=arama_lisansi)
        except Exception as e:
            print("ARAMA HATA (lisans %s, offset %d):" % (arama_lisansi, offset), e)
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        total = res.get("total") if total is None else total
        items = res.get("hits") or []
        if not items:
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0
            continue
        for h in items:
            pid = str(h.get("id"))
            if pid in seen:
                continue
            seen.add(pid)
            if pid in mevcut:
                continue
            name = (h.get("title") or "").replace("\n", " ")
            slug = h.get("slug") or ""
            tags = " ".join(h.get("tags") or [])
            lic = h.get("license") or ""
            dl = h.get("downloadCount") or 0
            likes = h.get("likeCount") or 0
            if not mw.satilabilir(lic):
                elenen_nc.append((pid, lic, name)); continue     # satilamaz -> populerlik DELMEZ
            # \bMARKA\b tam-kelime alaka testi (baslik + etiket + slug)
            if not marka_geciyor(term, name, tags, slug.replace("-", " ")):
                elenen_marka.append((pid, name)); continue
            pop = mw.populer(dl, likes)
            if mw.is_nobypass(name):
                elenen_cop.append((pid, name)); continue         # logo/amblem/merch -> hep ele
            if mw.is_cop(name) and not pop:
                elenen_cop.append((pid, name)); continue         # cop VE populer degil -> ele
            bulunan.append((pid, lic, name, dl, likes, mw.is_cop(name)))
            lisans_bulunan += 1
            # keeper-cap SADECE derin-olmayan (eski) modda dongoyu keser
            if not derin and lisans_bulunan >= maxn:
                break
        offset += LIMIT
        if (total and offset >= total) or (not derin and lisans_bulunan >= maxn):
            toplam_eslesme += total or 0
            lisans_indeksi += 1
            offset, total, lisans_bulunan = 0, None, 0

    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, dl) azalan
    havuz_toplam = len(bulunan)   # kirpmadan ONCE toplanan gercek aday sayisi (kabul olcumu)
    if not derin:
        bulunan = bulunan[:maxn]
    elif cikis_limiti is not None:
        bulunan = bulunan[:cikis_limiti]

    if elenen_nc:
        print("--- SATILAMAZ elenen %d (Standard/Exclusive/NC/bilinmeyen — populerlik DELMEZ) ---" % len(elenen_nc))
        for pid, lic, name in elenen_nc[:15]:
            print("  x %-9s %-32s %s" % (pid, ("[" + str(lic)[:30] + "]"), name[:48]))
    if elenen_marka:
        print("--- MARKA-ALAKASIZ elenen %d (\\b%s\\b tam kelime degil) ---" % (len(elenen_marka), term))
        for pid, name in elenen_marka[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur/kit-card; populer OLMAYAN) ---" % len(elenen_cop))
        for pid, name in elenen_cop[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[5])
    kirpma = "" if cikis_limiti is None else " (cikis %d'e kirpildi; havuz %d)" % (len(bulunan), havuz_toplam)
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, satilamaz %d, "
          "marka-alakasiz %d, cop %d elendi; populer-cop ISTISNA %d)%s ==="
          % (term, len(bulunan), toplam_eslesme, len(mevcut & seen), len(elenen_nc),
             len(elenen_marka), len(elenen_cop), pop_cop, kirpma))
    # KESIF MUHASEBESI — sayilar hukmu besleyen AYNI kovalardan turer (ikinci sayim yok).
    havuz = {"adaylar": [b[0] for b in bulunan], "elenen_cop": elenen_cop,
             "elenen_nc": elenen_nc, "elenen_marka": elenen_marka,
             "zaten_ekli": sorted(mevcut & seen)}
    print("GORULEN (hukum verilmis) %d · KARARSIZ (marka metinde yok; MODEL terimiyle "
          "YENIDEN taranmali, 'gorulen' SAYILMAZ) %d"
          % (len(gorulen_idler(havuz)), len(kararsiz_idler(havuz))))
    for pid, lic, name, dl, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %-9s %-14s ♥%-5d ⭳%-6d %s%s" % (pid, str(lic)[:14], likes, dl, name[:50], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    # Geriye uyumlu: eski cagri `makerworld-ara.py "<terim>" [max]` aynen calisir (derin=False).
    #  --derin : keeper-cap'i KALDIR, ham havuzu (offset<3000 tavanina/total'a kadar) TAM tara.
    #            derin modda pozisyonel sayi = OPSIYONEL cikis-trim (verilmezse tum havuz).
    args = sys.argv[1:]
    derin = "--derin" in args
    pos = [a for a in args if a != "--derin"]
    if not pos:
        sys.exit('Kullanim: python3 tools/makerworld-ara.py "<marka/terim>" [max] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 250)
