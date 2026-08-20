# SPEC — K214 EK EKSEN: `claude` sert bloğu EMEKLİ kolunca GÖLGELENİYOR mu?

> 🔴 **AĞAÇ:** `/Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215`
> 🔴 **GERÇEK dosyalara YAZMA.** Mutant vakaları KOPYA ağaçta koşar, iş bitince kopya SİLİNİR.

## Ölçülen yapı (mimar okudu, ben doğruladım)
`tools/mimar-icra-kapisi.py`:
```
:538  # 🔴 SIRA ONEMLI: 'claude' EMEKLI DEGILDIR — ... bu kol ona DOKUNMAZ.
:540  if emekli_motor_mu(motor):
:541      return emekli_gerekcesi(motor)
:543  if (motor == "claude" and EV_ADI in SERT_BLOK_EVLER and
:544          os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):
:547  if motor == "claude":
```
:538'deki güvence bir **YORUM**'dur. Yorum ölçüm değildir → makineye bağlanacak.

## ⓐ VAKA: `claude` emekli DEĞİL (tek kaynaktan türetilmiş hâliyle)
`mimar_kimlik.emekli_motor_mu("claude")` **False** olmalı; `"claude" in ISCI_MOTORLARI` **True**;
`"claude" in EMEKLI_ISCI_MOTORLARI` **False**. Üçünü de ayrı ayrı yaz.

## ⓑ VAKA: sert blok HÂLÂ REDDEDİYOR (emekli kolu eklendikten SONRA)
KraL (`/Users/okan/dev/pruvo`) ve MaCiT (`/Users/okan/dev/pruvo-hasat`) bağlamında
`isci.sh claude <ev> <spec>` çağrısı **REDDEDİLMELİ** ve reddin **`SERT_BLOK`** kolundan
geldiği gösterilmeli (`PRUVO_CLAUDE_ISCI_IZNI` ortamda YOKKEN).
🔴 Kimlik ekseni sökülsün ve söküm DOĞRULANSIN (`kimlik_ekseni(...)` = `None`), yoksa
`MUAF_BAGLAM` yaz — "YEŞİL" YAZMA. ([[prob-kendi-baglamini-olcer]])

## ⓒ MUTANT (asıl kanıt — [[ad-iki-rolde-mutanti-golgeler]])
KOPYA ağaçta `EMEKLI_ISCI_MOTORLARI`'na **`"claude"` EKLE** (mutant).
Sonra ⓑ'deki iki çağrıyı tekrar koş ve **REDDİN HANGİ KOLDAN geldiğini** karşılaştır:
- mutantsız: red metni **sert blok** kolundan mı?
- mutantlı: red metni **`emekli_gerekcesi`** kolundan mı?

🔴 **HÜKÜM BURADA VERİLİR — "reddedildi" YETMEZ, KOL DEĞİŞTİ Mİ ona bak.**
İki hâlde de "reddedildi" çıkarsa bu **kolun ölçülemez olduğunu** gösterir (mutant hedefiyle
birlikte düşüyor = tautoloji), **kolun sağlam olduğunu DEĞİL.** Bulduğunu OLDUĞU GİBİ yaz.

🔴 **YÖN UYARISI (önyargı kurma):** erken `return` reddi GEVŞETMEZ, SIKILAŞTIRIR
(emekli kolu da reddediyor). Yani risk "kapı yasak yolu açar" değil, **"sert blok kolu
ÖLÇÜLEMEZ hâle gelir"** olabilir. Hangisi olduğunu ÖLÇ, varsayma.

## ⓓ Kalıcı kabul
Bulguya göre ⓐ+ⓑ+ⓒ'yi `tools/mimar-kilit-test.py`'ye (ya da mevcut uygun bataryaya) VAKA olarak
EKLE ki bir daha yoruma değil teste bağlansın. Sonra bataryayı koştur, rc + sayaç satırını yaz.

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik adla worktree köküne yaz (ad CLAUDE.md
İLETİŞİM PROTOKOLÜ bölümünde). Var olan raporun ÜSTÜNE YAZMA — **EK BÖLÜM** olarak ekle.
Her satırın arkasında koştuğun komut + rc olsun. Ölçemediğine `ÖLÇÜLEMEDİ + sebep` yaz.
Temizlik: kopya ağacı sil ve silindiğini `ls` ile kanıtla.
