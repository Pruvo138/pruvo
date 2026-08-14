# DEVAM (KraL) — 8 Agu 2026

## 14 Agu 2026 — 🟢 KAPANIS: YAYIN ACILDI + YEDEK GERI GELDI (KraL, interaktif)

**HUKUM KOSUMDAN GELDI:** `Build & deploy` kosumu **`31792482488`** (HEAD `b2e8eb58`) →
**SUCCESS**, **6/6 job yesil** (`serit-a2` · `serit-a3` · `serit-a4` · `build` · `deploy` ·
`yayin`). `deploy` ve `yayin` **skipped DEGIL, KOSTU.** Bu, K98 (serit-a3) + K85 (serit-a2)
onarimlarini birlikte tasiyan ILK kosum.

**ONCE / SONRA (durum.py bolum 9):**
- ONCE: 🔴 **TIKALI (rc 3)** — canli main'den **6 commit** geride, en eski bekleyen **115 dk**,
  2 ardisik kosum yayinlamadan bitmis, son yayinlanan `dd68cd7a`.
- SONRA: 🟢 **AKIYOR (rc 0)** — 1 commit bekliyor (2 dk), ardisik iptal 0, ardisik hata 0,
  son yayinlanan **`b2e8eb58`**.

**YEDEK (bolum 7):** ONCE "ÖLÇÜLEMEDİ + YARIM KALMIS YEDEK" → SONRA **"taze: son yedek 3 dk
once — memory 227 + skills 19 + repo 4"**. `86e7a035`. Kok neden macOS izni DEGILMIS: eski
`backup/` altindaki Drive nesneleri bizim kimligimizle kullanilamiyordu (yeni dosya
olusturma/ezme/silme SERBEST ama **listeleme EPERM**). Taze kok (`backup-v2`) sinifi atladi;
kok adi artik bes yerde degil TEK SABIT ve `durum.py` de ondan TURETIYOR.

**BOLUM 8:** kancalar **18 eksen yesil**. **BOLUM 3:** artik dal **0**.
**Katalog 27066** (MaCiT d7 dilimi +65 canliya girdi, ayni pencerede).

**OKAN'DA KALAN (1):** eski `<Pruvo>/backup` klasoru Drive arayuzunden `backup-v2/` icine
surukle-birak ile tasinacak (`os.rename` EPERM verdi; SILINMEDI, yerinde duruyor).

**🟢 KAPANDI — `media.pruvo3d.com` PURGE BORCU YOKMUS (iddia CURUDU, token GEREKMEDI).**
Defterdeki kalem "son partide 38 gorselin 19'u 404 (`cf-cache-status: HIT`), 100'luk ornekte
17, **TTL 1 YIL kendiliginden duzelmez**, tekil purge + Zone.Cache Purge token'i gerekir"
diyordu. **IKI BAGIMSIZ EKSENDE olculdu, 404 SAYISI SIFIR:**
- bilinen-arizali parti: id'si `c3d-` ile baslayan **58 urunun 127 gorselinin 127'si 200**
  (ayni kume onceden 19/38 404 vermisti);
- katalogun EN ESKI **1500** URL'i → **1500'u 200**;
- ilk sondada en YENI 1500 URL'i → **1500'u 200**. Toplam **3127 URL, 404 = 0, ARIZA = 0**.
Ornek cevabin `cf-cache-status` degeri **MISS** — yani bu uc CDN'de uzun sureli tutulmuyor.
**Kok yanlis: "Cloudflare 404'u 1 yil onbellekte tutar" cikarimi.** `max-age=31536000`
BASARILI cevabin basligiydi; negatif cevabin omru cok daha kisadir ve kendiliginden dustu.
Gercek kok neden (`47389674`, readback'in CDN yerine S3 sondasina alinmasi) zaten yeni
negatif kayit URETILMESINI durdurmustu; kalan sey bekleyerek gecti.
⚠️ KAPSAM DURUSTLUGU: bu olcum **bu makinenin bagli oldugu CDN noktasindan**. Negatif
onbellek noktaya ozeldir; hukum "olculen kapsamda borc YOK"tur, "her noktada temiz" DEGIL.

**🔴 UCUNCU DERS (bugunun uctan ucuncusu):** *bir alarmin SAYISI dogru olabilir ama
CIKARIMI yanlis olabilir.* "19/38 404" olcumdu ve dogruydu; "TTL 1 yil, kendiliginden
duzelmez" ise CIKARIMDI ve yanlisti — ve gunlerce bir Okan-kapisi acik tuttu, hatta bugun
bir kez de gereksiz sistem-ayari istettirdi. Alarmi kapatmadan once **olcumu degil
cikarimi** yeniden sorgula.

**ArTisT'e DEVREDILDI (Okan karari):** attribution sorusu cevaplandi + arastirma alani ona
gecti; **K99** acildi (REF ↔ siparis bag kolonu YOK; spec ArTisT'te, Worker/D1 tarafi bende).

**🔴 GUNUN IKINCI DERSI:** *"izin verildi ama hala duser"de siradaki soru "hangi ISLEM
reddediliyor"dur.* Olusturma / ezme / silme / listeleme AYRI haklardir; biri reddedilirken
otekiler serbest olabilir. "Klasor yazilabilir mi" sorusu bu vakada UC KEZ yanlis yonlendirdi
ve bir kez de Okan'dan gereksiz yere sistem ayari istettirdi. Hipotezi degil **islemi** olc.

## 14 Agu 2026 ~11:10Z — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → rc=0 · `GITHUB_BILDIRIM_INBOX=3 BULUNAN=3 TASINAN=3 ATLANAN=0 CIKAN=3 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=337:2026-08-14T12:37:34 HUKUM=SUPURULDU`. 3 mail (Build & deploy `ca146ce` · Paket tazeligi `ca146ce` · D1 uzlastirici `ebebb96`).
COP_DENETIM: `MESRU=105 YANLIS=0 KAPSAM=105 ATFEDILMEYEN=25` → yanlis supurme izi YOK.

CI BAGIMSIZ TEYIT (HEAD `ca146ced`): 3 koşum kırmızı: `Build & deploy serit-a2` (pre-push D1 kaynagi kabul testi) + `serit-a3` (Kanca kablosu davranis ayagi) + `Paket tazeligi` (adım-4 yayin gecikmesi + adım-9 iş bayatligi). 14:08 kod 116128af itildi (Okan emriyle); K98 (89941482) + K85-kapsam (6ee9ead2) + dal/oturum temizligi (b2e8eb5) geldi — `Build & deploy` YENI koşum (`31792482488`) **YESIL**, TÜM steps (serit-a2, serit-a3, serit-a4, build, deploy, yayin) basarili. CI zinciri çalışıyor; K91 (Odeme bayatlik) hâlâ OKAN-KAPISI (deploy kararı).

§4.7.1 ONARIM KAPISI: `nobet-kapi.py --tur` → `HUKUM=ONCEKI_TUR_SURUYOR` (H7 kilidi, pid 72074). Codex spec'i scratchpad'e yazıldı (`/Users/okan/.claude/scratchpad/spec-kanca-kablo-kapsam.md`); Codex türetilirken K98 Okan tarafından itildi, **DEGISEN_DOSYALAR=YOK; yabancı K98 değişiklikleri korundu, YENI_KOSUM=YOK:BLOCKED**. K98 → K85 → b2e8eb5 ile sınıf kapandı.

TAMIRCI BAKIM: bu turda K98 dagitildi+kapandi (KraL+Codex+Okan is birligi); K91 OKAN-KAPISI (madde 6); bakim 0/0.
OKAN'A ÇIKIŞ: YOK (§5 — tüm Okan kararı gerektiren kalemler zaten K98 ile kapandı, K91 OKAN-KAPISI sinifinda).
