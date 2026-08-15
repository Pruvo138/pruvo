# GÖREV 2 — Ölçüm/teşhis (fikstür log'u)

> Koşucu, `<CALISMA>` yerine gerçek geçici dizin yolunu yazar.

Dosya: `<CALISMA>/isci-fiksturu.log` — işçi turlarının log'u. Biçim:
`=== <zaman> BASLANGIC motor=<m> ev=<e> etiket=<t> ===` ile başlar,
tur normal biterse `=== <zaman> BITIS rc=<n> sure=<sn> ===` satırı yazılır.

ÖLÇ:
1. BASLANGIC'ı olup ARDINDAN BITIS satırı OLMAYAN turların sayısı.
2. Bu turların motor kırılımı (motor başına sayı).
3. Bitişsiz turlardan sonra gelen ilk turun zaman farkı hep aynı mı? Aynıysa o farkı saniye
   olarak yaz — bu bir tur zaman aşımı tavanının kanıtıdır.

Hiçbir dosyayı değiştirme, ağ çağrısı yapma.

## KABUL — son satır
BITISSIZ=<sayi> · MOTOR_KIRILIMI=<motor:sayi,motor:sayi> · TAVAN_SN=<sayi ya da YOK>
