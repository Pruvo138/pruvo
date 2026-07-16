# TABAN FİYAT TABLOSU — Okan dolduracak (sarı seri konfigüratör)

Taban fiyat = ürünün **varsayılan ölçülerdeki PLA (Siyah/Beyaz/Gri)** satış fiyatı.
Diğer her şey formülden türetilir: `fiyat = tabanFiyat × (hacim/tabanHacim) ×
filamentKatsayı × renkFaktör` (PLA 1.00 / PETG 1.30 / ABS 1.50 / TPU 1.55 /
ASA 1.60 / Karbon 2.00; Diğer renk ×1.15). Kuruş korunur, yuvarlama yok.

Fiyat girilene kadar sitede o ürünün fiyatı "—" görünür (sipariş WhatsApp'la sürer).
Doldurulan fiyat `jenerator/urunler/<id>.json` içindeki `tabanFiyatTL` alanına yazılır.

| Ürün | Varsayılan ölçüler | Taban hacim | Taban fiyat (PLA) |
|---|---|---|---|
| Kişiye Özel Jeton / Poker Çipi / Madalyon | Çap=39 mm, Kalınlık=3.4 mm, Yazı stili=gomme, İşlenen yüz=tek, Kenar deseni=segmentli | 3.9 cm³ | **___ TL** |
| Ölçüye Özel Birleştirme Konektörü / Modüler Eklem (Çubuk · Boru · Profil) | Kol sayısı=3, Kol kesiti=yuvarlak, Çubuk veya boru çapı=10 mm, Kol boyu=25 mm, Cidar kalınlığı=2.5 mm, Geçme toleransı=normal | 6.9 cm³ | **___ TL** |
| Ölçüye Özel Cetvel / Gönye (Düz · Üçgen · L Gönye) | Cetvel tipi=duz, Ölçü sistemi=metrik, Uzunluk=15 cm / inç, Genişlik=30 mm, Kalınlık=3 mm, İşaret stili=oyma | 14.3 cm³ | **___ TL** |
| Ölçüye Özel Damga / Kaşe (Yazı · Logo · Şekil) | Yazı boyutu=8 mm, Kenar payı=5 mm, Kaşe biçimi=dikdortgen, Kabartma derinliği=1.4 mm, Sap seçimi=sapli | 12.1 cm³ | **___ TL** |
| Ölçüye Özel Huni (Mutfak · Atölye · Açılı Uç · Laboratuvar) | Ağız çapı=100 mm, Koni yüksekliği=60 mm, Akıtma ucu çapı=14 mm, Akıtma ucu boyu=54 mm, Uç kesim açısı=0 ° | 20.4 cm³ | **___ TL** |
| Ölçüye Özel Izgara / Havalandırma Menfezi / Kapak | Ürün tipi=panjur, Delik şekli=elips, Dış en=100 mm, Dış boy=100 mm, Gövde derinliği=10 mm, Panjur açısı=0 ° | 40.4 cm³ | **___ TL** |
| Ölçüye Özel Montaj Braketi / Köşe Bağlantısı (Açılı · L · T · Y · Köşe · Düz) | Braket tipi=acili, İç açı=90 derece, Kalınlık=4 mm, Kol genişliği=20 mm, Kol uzunluğu=40 mm, Kol başına delik sayısı=2 | 7.1 cm³ | **___ TL** |
| Ölçüye Özel O-Ring / Conta (Sızdırmazlık Halkası) | İç çap=30 mm, Kesit çapı / kalınlığı=3.6 mm, Kesit profili=yuvarlak | 1.1 cm³ | **___ TL** |
| Ölçüye Özel Pervane / Fan / Çark (İmpeller) | Pervane çapı=150 mm, Kanat sayısı=3 adet, Mil çapı=5 mm, Mil bağlantısı=duz, Burun konisi=yok, Dış ring=yok | 7.9 cm³ | **___ TL** |
| Ölçüye Özel Petek / Delikli Panel & Grid (Altlık · Filtre · Menfez) | Uygulama modu=delikli, Desen=petek, Panel eni=80 mm, Panel boyu=60 mm, Panel kalınlığı=3 mm, Göz / delik boyutu=6 mm | 10.2 cm³ | **___ TL** |
| Ölçüye Özel Profil / Kiriş / Ekstrüzyon (I-Beam, T-Slot, Boru) | Kesit tipi=i, Kesit yüksekliği=40 mm, Kesit genişliği=30 mm, Et kalınlığı=3 mm, Profil uzunluğu=100 mm, İç yapı=bos | 28.2 cm³ | **___ TL** |
| Ölçüye Özel Rampa / Şim / Takoz (Seviye & Denge) | Genişlik / en=40 mm, Uzunluk / boy=80 mm, Yükseklik=20 mm, Eğim belirleme yöntemi=yukseklik, Eğim açısı=15 °, Üst yüzey=duz | 32.0 cm³ | **___ TL** |
| Ölçüye Özel Rulman / Bilyalı Yatak (Plastik Bearing) | İç çap=10 mm, Dış çap=30 mm, Genişlik=9 mm, Yuvarlanma elemanı=bilya, Çalışma boşluğu=0.15 mm, Flanş=yok | 4.8 cm³ | **___ TL** |
| Ölçüye Özel Triger / Kayış Kasnağı (GT2 · HTD · Timing Pulley) | Kayış profili=gt2_2mm, Diş sayısı=20 adet, Kayış genişliği=10 mm, Mil bağlantısı=duz, Mil çapı=5 mm, Yan flanş=iki_taraf | 1.2 cm³ | **___ TL** |
| Ölçüye Özel Triger / Kayış (GT2 · HTD · Kapalı Döngü ya da Düz) | Diş profili=GT2_2mm, Kayış şekli=kapali, Diş sayısı=60 adet, Kayış genişliği=6 mm, Diş tarafı=ic | 0.8 cm³ | **___ TL** |
| Ölçüye Özel Vida / Cıvata · Somun · Pul · Dişli Mil (Saplama) | Parça tipi=civata, Nominal M ölçüsü=5 mm, Boy=20 mm, Geçme boşluğu=0.2 mm | 0.5 cm³ | **___ TL** |
| Ölçüye Özel Yay / Dalga Yay / Flexure (Bası · Çekme · Serpantin) | Yay tipi=spiral, Dalga formu=sinus, Serbest boy=60 mm, Dış çap=20 mm, Tel çapı=3 mm, Dalga elemanı boyu=60 mm | 3.0 cm³ | **___ TL** |
| Ölçüye Özel Dişli & Kramayer (Düz · Helis · Konik · Sonsuz · İç Dişli) | Dişli tipi=duz, Diş sayısı=40 adet, Modül=1.25 mm, Kalınlık=7 mm, Mil deliği çapı=6 mm | 13.4 cm³ | **___ TL** |

*Bu dosya `python3 jenerator/test/fiyat-tablosu-uret.py` ile şemalardan üretildi;
elle fiyat işlendikten sonra yeniden üretirsen fiyatlar şemadan gelir (kaybolmaz).*
