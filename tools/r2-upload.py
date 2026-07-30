#!/usr/bin/env python3
"""
Pruvo R2 görsel yükleyici.
Kimlik bilgileri repo kökündeki gitignore'lu .r2-credentials.json dosyasından okunur
(bu betiğin içinde SIR YOKTUR — public repo'ya güvenle commit edilebilir).

Kullanım:
    python3 tools/r2-upload.py <yerel_dosya> <r2_anahtari>
Örnek:
    python3 tools/r2-upload.py /tmp/x.jpg urunler/audi-parca-1.jpg
    -> https://media.pruvo3d.com/urunler/audi-parca-1.jpg

Birden fazla dosya için çift çift ver:
    python3 tools/r2-upload.py a.jpg urunler/a.jpg b.jpg urunler/b.jpg

DOĞRULAMA (sessiz-yükleme kalkanı — put_object çağrısı REFAKTÖR EDİLMEDİ, etrafına sarıldı):
  R1 Ön-doğrulama (fail-closed): gövde bilinen görsel sihirli-baytıyla başlamalı + asgari boyutu geçmeli
     → 0-bayt / MIN_BOYUT altında / görsel-magic-yok / Cloudflare-403 HTML gövdesi yükleme ÖNCESİ ölür
       (yükleme YAPILMAZ, RAISE).
  R2 ContentType gövdeden türetilir (sabit "image/jpeg" DEĞİL) → feed/og:image/sosyal kazıcı kırılmaz.
  R3 Uzantı↔gövde uyuşmazlığı (.jpg ad ama PNG gövde) → stderr LOUD uyarı + content-type GERÇEK formata göre.
     Varsayılan hard-reject ETMEZ (MaCiT/KaaN partisini ortada kırmasın).
  R4 Upload SONRASI head_object readback (fail-closed): R2'deki ContentLength == yerel boyut değilse RAISE
     → kısmi / başarısız PUT (R2 boyutu != yerel boyut) yakalanır.
  Piksel-decode DOĞRULANMAZ; yerelde önceden kesilmiş ama magic-geçerli dosya yakalanmaz.

  R5 SİLME sonrası BAĞIMSIZ varlık doğrulaması (`sil_ve_dogrula`, fail-closed) →
     aşağıdaki "SESSİZ SİLME" notuna bak. Silme aracının kendi "başarılı" beyanına ASLA güvenilmez.

🔴 SESSİZ SİLME SINIFI (30 Tem 2026'da ÖLÇÜLDÜ, tahmin değil — `pruvo-ozel` kovasında üretildi):
  R2 nesne okuma ucu Cloudflare kenar ÖNBELLEĞİ arkasındadır (ölçüm: aynı cevapta
  `CF-Cache-Status: HIT`). Bir nesnenin gövdesi bir kez okunduktan sonra:
    · `delete` çağrısı BAŞARILI döner ve nesne origin'de GERÇEKTEN silinir,
    · ama sonraki okumalar ÖNBELLEKTEN eski gövdeyi 200 ile vermeye devam eder (7+ dakika ölçüldü),
    · istemci tarafı `Cache-Control: no-cache` bunu DELMEZ; sorgu parametresi ile önbellek
      kırma da imkânsızdır (uç, sorgu dizesini anahtarın parçası sayıp 404 verir).
  ⇒ "Sildim ama duruyor" teşhisi YANLIŞTIR: silme değil DOĞRULAMA sessizce hatalıdır.
  İki ayrı sessiz-başarı sinyali daha ölçüldü, ikisi de hiçbir bilgi taşımaz:
    · `wrangler r2 object delete` HİÇ VAR OLMAMIŞ anahtar için de RC=0 + "Delete complete." basar.
    · `wrangler r2 object get` anahtar YOKKEN bile `--file` hedefini 0 baytla OLUŞTURUR (RC=1) →
      "dosya var mı" diye bakan doğrulama SAHTE POZİTİF verir. Varlık testi BOYUTA bakmalıdır.
  Bu yüzden R5 varlığı BAĞIMSIZ bir sonda (`var_mi`) ile ölçer ve hâlâ varsa KIRMIZI yanar;
  önbellekten gelen bayat "hâlâ var" cevabı da KIRMIZI üretir — yön bilinçli fail-closed'dır
  (sahte YEŞİL "silindi" demektense sahte KIRMIZI ile durmak yeğlenir).
"""
import sys, os, json, time, boto3

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", ".r2-credentials.json")

# R1 asgari boyut: 1024 bayt. Gerçek ürün görselleri (JPEG/PNG/WebP) daima kByte'larca olur;
# 0-bayt, kesik yazma ve Cloudflare-403 HTML gövdeleri bu eşiğin altında ya da geçerli-magic'siz kalır.
# Meşru görsel bu eşikten kolayca geçer → false-reject yok.
MIN_BOYUT = 1024

# Format anahtarı → HTTP content-type
CONTENT_TYPE = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def format_belirle(data):
    """Gövdenin sihirli baytından görsel formatını döndür ('jpeg'/'png'/'webp') ya da None (bilinmeyen/çöp)."""
    if data[:3] == b"\xff\xd8\xff":                      # JPEG: FF D8 FF
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":                 # PNG: 89 50 4E 47 0D 0A 1A 0A
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WebP: RIFF....WEBP
        return "webp"
    return None


def uzanti_format(key):
    """R2 anahtar/ad uzantısından beklenen format ('jpeg'/'png'/'webp') ya da None."""
    k = key.lower()
    if k.endswith(".jpg") or k.endswith(".jpeg"):
        return "jpeg"
    if k.endswith(".png"):
        return "png"
    if k.endswith(".webp"):
        return "webp"
    return None


def on_dogrula(data, key):
    """R1 + R2 + R3: gövdeyi doğrula, ContentType döndür. Geçmezse RAISE (yükleme ÖNCESİ)."""
    # R1a boyut
    if len(data) < MIN_BOYUT:
        raise ValueError(
            "R1 red: %s boyut %dB < %dB asgari (0-bayt / kesik yazma / 403-HTML govdesi) — yukleme yapilmadi"
            % (key, len(data), MIN_BOYUT)
        )
    # R1b sihirli-bayt
    fmt = format_belirle(data)
    if fmt is None:
        raise ValueError(
            "R1 red: %s bilinen gorsel sihirli-bayti yok (JPEG/PNG/WebP degil — muhtemelen HTML/coplu govde) — yukleme yapilmadi"
            % key
        )
    # R2 ContentType gövdeden
    content_type = CONTENT_TYPE[fmt]
    # R3 uzantı↔gövde uyuşmazlığı → LOUD uyarı (hard-reject DEĞİL)
    uf = uzanti_format(key)
    if uf is not None and uf != fmt:
        print(
            "UYARI: %s uzantisi .%s ama govde %s — feed reddedebilir, content-type %s olarak yukleniyor, dosyayi %s'e cevir"
            % (key, uf, fmt.upper(), content_type, uf),
            file=sys.stderr,
        )
    return content_type


def readback_dogrula(s3, bucket, key, yerel_boyut):
    """R4: put_object SONRASI head_object ile boyut teyidi (fail-closed). Uyuşmazsa RAISE."""
    head = s3.head_object(Bucket=bucket, Key=key)
    r2_len = head.get("ContentLength")
    if r2_len != yerel_boyut:
        raise ValueError(
            "R4 red: readback boyut uyusmuyor: yerel %s, R2 %s — yukleme eksik/kismi PUT"
            % (yerel_boyut, r2_len)
        )


def s3_var_mi(s3, bucket):
    """boto3 istemcisinden R5 için varlık sondası üretir: var_mi(key) -> bool.

    head_object 404/NoSuchKey/ClientError(404) → YOK; başarı → VAR. Başka hata TÜRLERİ
    (yetki, ağ) YUTULMAZ, yukarı fırlar: "yetkim yok" ile "nesne yok" karıştırılırsa
    silme doğrulaması sessizce fail-open olur."""
    def var_mi(key):
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return True
        except Exception as exc:
            kod = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            durum = (getattr(exc, "response", {})
                     .get("ResponseMetadata", {}).get("HTTPStatusCode"))
            if str(kod) in ("404", "NoSuchKey", "NotFound") or durum == 404:
                return False
            raise
    return var_mi


def sil_ve_dogrula(key, var_mi, sil, dene=3, bekle=None, aralik=(2.0, 5.0)):
    """R5: SİL → sonra BAĞIMSIZ olarak yokluğunu DOĞRULA. Fail-closed.

    Silme aracının çıkış kodu / "Delete complete." mesajı KABUL DELİLİ DEĞİLDİR
    (modül docstring'indeki SESSİZ SİLME notu: olmayan anahtar için de başarı basılır).
    Kabul yalnızca `var_mi(key)` silmeden SONRA False dönerse verilir.

    Bağımlılıklar ENJEKTE edilir → nöbetçi/kabul testi AĞSIZ koşar ve gerçek silme
    yolu (boto3 ya da wrangler) hangisi olursa olsun aynı kapı kullanılır:
      var_mi(key) -> bool     bağımsız varlık sondası (bkz. s3_var_mi)
      sil(key)    -> None     asıl silme çağrısı (delete_object / wrangler delete)

    Dönüş: "zaten-yoktu" | "silindi-dogrulandi".
    RAISE: silmeden sonra nesne HÂLÂ görünüyorsa (bütçe dolunca) → KIRMIZI.
    """
    bekle = bekle or time.sleep
    if not var_mi(key):
        # Silme ÇAĞRILMAZ: "silindi" demek yanlış olurdu (olmayan anahtarın silinmesi
        # de başarı raporlar; sahte başarıyı kaynağında keseriz).
        return "zaten-yoktu"
    sil(key)
    for i in range(dene):
        if i:
            bekle(aralik[min(i - 1, len(aralik) - 1)])
        if not var_mi(key):
            return "silindi-dogrulandi"
    raise ValueError(
        "R5 red: %s SILINDI DENDI ama %d bagimsiz kontrolde de HALA VAR — silme "
        "uygulanmadi YA DA okuma bayat onbellekten geliyor (bkz. SESSIZ SILME notu). "
        "Kaynak dogrulanmadan 'silindi' RAPORLANMAZ." % (key, dene)
    )


def dogrula_ve_yukle(s3, bucket, key, data):
    """Tek dosyayı doğrula → yükle → readback ile teyit et. content_type döndürür."""
    content_type = on_dogrula(data, key)          # R1 + R2 + R3 (fail-closed önce)
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)  # yazma yolu (refaktör YOK)
    readback_dogrula(s3, bucket, key, len(data))  # R4 (fail-closed sonra)
    return content_type


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print("Kullanim: r2-upload.py <yerel_dosya> <r2_anahtari> [<yerel> <anahtar> ...]")
        sys.exit(1)
    cfg = json.load(open(CFG_PATH))
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
    )
    for i in range(0, len(args), 2):
        local, key = args[i], args[i + 1]
        with open(local, "rb") as f:
            data = f.read()
        dogrula_ve_yukle(s3, cfg["bucket"], key, data)
        print(cfg["public_base"] + "/" + key)


if __name__ == "__main__":
    main()
