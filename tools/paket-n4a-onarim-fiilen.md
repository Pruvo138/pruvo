# PAKET — N4A: onarım hattı FİİLEN onarsın (chip: `KraL-N4A`)

> Kurgunun en zor kalemi (Okan seçti). Kaynak: `memory/nobet-onarim-kurgusu.md` — Okan'ın
> bağlayıcı cümlesi: *"sözde değil özde çalışan bir sistem istiyorum… önceki çalışmayan sistemi
> kurmak günler aldı… sonuç karpuz kabuğu oldu."*
> Bu paket tam olarak o cümlenin ölçülebilir hâlidir: hat **ölçüyor ama onarmıyor**.

## 1. MİMARIN ÖLÇTÜĞÜ OLGULAR (20 Ağu ~07:1xZ, KraL — hatırlama değil)

| kaynak | ölçüm |
|---|---|
| `~/.claude/cron/nobet-onarimsiz-sayac.json` | **`ustuste_onarimsiz: 104`** — düşmüyor, ARTIYOR |
| `~/.claude/cron/gozcu-kalp.json` | `icra_rc: 1` · `dagitilabilir: 1` · `kat_mimar: 10` · `kat_isci: 1` · `kat_okan: 1` · `llm_turu: true` · `tetik: CI_KIRMIZI` · `sahip: KraL` · `sahip_sebep: tek-serit` · `hedef_run: 32341799689` |
| `~/.claude/cron/gozcu-eskalasyon.md` | **9 kayıt**, hepsi `deneme=3 DURUM=ESKALASYON`, **6'sı 20 Ağu'da** |
| crontab | gözcü `8,23,38,53` (15 dk) ✅ · `ci-nobeti.sh` `7 * * * *` hâlâ ateşliyor (tetik `nobet-tetik.py`'de) |
| kalp tazeliği | `KALP=TAZE` — fail-loud kolu çalışıyor |

**Okunuşu:** gözcü doğru karar veriyor (yeşilde `LLM_TURU=0`, kırmızıda `1`), sahip atanıyor,
dağıtılabilir işaretleniyor — ama **icra rc=1** ve **104 turdur hiçbir kırmızı kapanmıyor**.

## 2. SIRA — BOZMA (önce teşhis, sonra onarım)

1. 🔴 **ÖNCÜL TAZELE:** yukarıdaki beş sayıyı **kendin yeniden ölç** ve yaz. Sayılar oynamış
   olabilir; bayat öncülle iş kurma ([[spec-oncul-kapsam-on-olcumu]]).
2. **`icra_rc=1`'in SEBEBİNİ ölç:** icra hangi adımda, hangi çıkış koduyla duruyor? Log satırıyla
   (`ci-nobeti.log` / `gozcu.log` / `isci.log`) ve kod satırıyla (`dosya:satır`) göster.
   "Muhtemelen kota" YETMEZ — 403 ise 403'ü gösteren satırı getir.
3. **9 eskalasyonun ortak paydasını çıkar:** kaç FARKLI sebep var? Aynı sebep tekrar mı ediyor,
   yoksa her biri ayrı mı? (Aynı sebebin 3. tekrarı ise tekil yama YASAK →
   [[ucuncu-tekrar-sinif-kapisi]].)
4. **Ancak bundan sonra onar.** Önce onarıp sonra açıklama yazma.

## 3. KABUL — beş madde, hepsi SAYIYLA

| # | kapatan ölçüm |
|---|---|
| ① | **EN AZ BİR gerçek kırmızı, hattın KENDİSİ tarafından uçtan uca onarıldı**: run-id + onarım commit'i + sonraki koşumun `conclusion=success`'i. Elle onarım SAYILMAZ. |
| ② | `ustuste_onarimsiz` **ölçülerek DÜŞTÜ**: önce/sonra sayısı **ve** sayacı düşüren kod yolu (`dosya:satır`) |
| ③ | 🔴 **Sayaç dürüstlüğü mutantı:** "onarım olmadan sayacı düşüren" bir yol enjekte edilince test **KIRMIZI** yanar. Sayacı elle sıfırlamak/dosyayı silmek **onarım DEĞİLDİR** ve bu mutantla yasaklanır. Mutantın **hedef kolu öldürdüğü ayrıca** kanıtlanır (K182). |
| ④ | `icra_rc` **yeşile döndü** ve yeşilliği **iki ARDIŞIK gerçek turda** görüldü (tek tur tesadüf olabilir) |
| ⑤ | `kat_mimar=10` **düştü**: kaç kalem işçi katına indi, hangileri (id listesi); inemeyen kaldıysa **kalem kalem gerekçe** |

## 4. YASAKLAR

- Sayaç dosyalarını **elle yazma/silme** · `gozcu-eskalasyon.md`'yi temizleme (**kanıttır**).
- **crontab'a DOKUNMA** — cron satırı Okan/BaBa düzlemi; değişmesi gerekiyorsa mimara yaz.
- `--no-verify` YOK · kapı bypass YOK · ana checkout'ta commit YOK · merge+push **MİMARDA**.
- **N3 (sahte eskalasyon tatbikatı) bu kalemin İÇİNDE DEĞİL** — ayrı kalem, ölçütünü büyütme.
- Okan'a doğrudan bildirim YOK; rapor mimara.

## 5. ÖLÇÜLEMEZSE

`OLCULEMEDI` + sebep + **"neyi ölçmek kapatır"**. Özellikle: işçi kotası (kimi 403) icrayı
düşürüyorsa bunu **sayıyla** göster — o zaman kalem "hat bozuk" değil **"kat yok"** olur ve
hüküm (tarife) Okan'a çıkar. İkisini karıştırma; fark bu kalemin en kritik ayrımıdır.

## 6. Kapanış

Sayılı kapanış `memory/mimar-posta-kutusu.md`'nin EN ÜSTÜNE, son satır birebir
`✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM`. Kurgu dosyası (`memory/nobet-onarim-kurgusu.md`) **SİLİNMEZ** —
silme şartı tüm kalemler + BaBa'nın açık onayı.
