# GÖREV 5 — Uzun bağlam tarama (çağrı grafı)

> Koşucu, `<CALISMA>` yerine gerçek geçici dizin yolunu yazar.

`<CALISMA>/kaynak/` altında bir Python ağacı var. `hesapla_taban_fiyat` fonksiyonunu
**kim çağırıyor** — hepsini bul.

- Tanımın kendisi çağrı DEĞİLDİR; sayma.
- Yorum satırındaki ve string içindeki geçişler çağrı DEĞİLDİR; sayma.
- Farklı adla import edilip (`as tf`) çağrılan yerler çağrıDIR; say.
- Dosya adı desenine güvenme, ağacın tamamını tara.

Çıktıya çağrı noktalarını `dosya:satir` biçiminde, **alfabetik sıralı**, virgülle ayrılmış yaz.
🔴 Yollar `<CALISMA>/kaynak/` dizinine **göreli** yazılır: `ana.py:4` (doğru) — `kaynak/ana.py:4`
ya da mutlak yol (yanlış).

Raporunun **son satırı kabul satırı olsun**; kabul satırından sonra `ONERI=` gibi ek satır yazma.

## KABUL — son satır
CAGRI=<sayi> · NOKTALAR=<dosya:satir,dosya:satir,...>
