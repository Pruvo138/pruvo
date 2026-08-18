# PAKET K152-B — `k152-link-temiz` dalı BAYAT tabandan yeniden uygulanıyor

**Mimar:** KraL · **Tarih:** 18 Ağu 2026
**Ağaç:** `/Users/okan/dev/pruvo/.claude/worktrees/k152-yeniden` (dal `kral/k152-yeniden`, taban güncel main)

## NEDEN MERGE DEĞİL, YENİDEN UYGULAMA (mimar hükmü)

Eski dal `k152-link-temiz` (`56269db4`) merge-base'i `2c092d5c` — **çok eski**. Ölçtüm:
`merge-tree` iki dosyada ÇAKIŞMA veriyor (`nobet.yml`, `DEVAM.md`). Sebep bugün doğdu:
K166 `nobet.yml`i BÜTÜN olarak yeniden yazdı ve `DEVAM.md` o tarihten beri defalarca döndü.
Eski dalı merge etmek, bayat `DEVAM.md` içeriğini geri getirir ([[yeniden-yazilmis-taban-merge-tuzagi]]).
Bu yüzden dal MERGE EDİLMEYECEK; **içeriği güncel taban üzerine yeniden uygulanacak.**

**Mimar zaten uyguladı (ağaçta hazır, `A` olarak duruyor):**
`tools/kaynak-link-tamamla.py` (326 satır) · `tools/kaynak-link-test.py` (718 satır) —
eski daldan BİREBİR alındı.

**Bilerek DÜŞÜRÜLEN:** eski dalın `DEVAM.md` hunk'ı (26 satır). Defter o tarihten bu yana
tamamen döndü; geri getirmek kapanmış kalemleri diriltirdi.

## İŞ 1 — CI kablosu (eski daldaki 9 satır, YENİ `nobet.yml`e)

Eski dal `nobet.yml`e şu iki adımı, `"Marka sayfasi artim + sayfa-ici model filtresi
(davranis, node)"` adımının HEMEN ARDINA eklemişti. Çapa güncel dosyada DURUYOR
(mimar ölçtü: `nobet.yml:1695`). Aynı yere, aynı yorum bloğuyla ekle:

```yaml
      # KAYNAK LINK TAMAMLA — K152 kabul + mutasyon bataryasi (17 Agu 2026).
      # Gizli kaynak defterindeki eksik uretici linkini tamamlar; urunler.json'a
      # dokunmaz. Hijyen ekseni: kirmizisi musteriye yanlis para odetmez, veri
      # sizdirmaz, siteyi durdurmaz.
      - name: "Kaynak link tamamlama: kabul testi (fikstur + gercek beyan)"
        run: python3 tools/kaynak-link-test.py
      - name: "Kaynak link tamamlama: mutasyon bataryasi"
        run: python3 tools/kaynak-link-test.py --mutasyon
```

🔴 **ŞERİT SEÇİMİ MİMAR HÜKMÜDÜR, DEĞİŞTİRME:** bu adımlar **SERIT B** (`nobet.yml`) içinde
kalacak. Gerekçe eski daldaki yorumun aynısı: kırmızısı müşteriye yanlış para ödetmez, veri
sızdırmaz, yayını durdurmaz. `deploy.yml`e TAŞIMA, bloklayıcı şeride terfi ETTİRME.
⚠️ Bugün tam da bunun tersi bir terfi yayını kapatmıştı (K166); şerit kararı ölçülmüş bir
hükümdür, "daha güvenli olsun" diye yukarı çekilmez.

## İŞ 2 — KABUL

```
python3 tools/kaynak-link-test.py              → rc=0
python3 tools/kaynak-link-test.py --mutasyon   → mutant tablosu; UYGULANAMADI varsa AYRI say
python3 tools/is-akisi-kapisi.py               → rc=0  (yeni adımlar beyan/gerçek ayrışması yaratmadı)
python3 tools/ci-kapsam-test.py                → rc=0  (yeni nöbetçi CI'da GERÇEKTEN koşuyor)
```

🔴 `ci-kapsam-test.py` bu paketin ANAHTAR kapısıdır: yeni bir nöbetçi dosyası geliyor ve
"CI'da koşuyor" iddiası ancak bu kapıyla kanıtlanır. Yorum satırı koşma sayılmaz.

🔴 **ARACIN KENDİSİ YAZICI MI, ONU DA ÖLÇ:** `kaynak-link-tamamla.py` gizli kaynak kayıt
düzlemine yazıyor. Bu turda onu **ÇALIŞTIRMA** (yazma turu DEĞİL); yalnız şunu raporla:
`urunler.json`'a dokunuyor mu, gizli düzleme yazarken kilit + atomik yazım kullanıyor mu,
çıktısında üyelik/tedarikçi değeri basıyor mu. Üç sorunun cevabı da ham koddan alıntıyla.
🔴 Çıktısında kayıt gövdesi/üyelik değeri BASIYORSA: DUR, yazma, mimara yaz.

## SINIR
- `urunler.json` / gizli kaynak düzlemi **DOKUNULMAZ**; `kaynak-link-tamamla.py` KOŞTURULMAZ.
- `deploy.yml`e DOKUNMA. `DEVAM.md`ye DOKUNMA.
- Kaynak kodu ONARMA; kırmızı bulursan raporla.
- Commit ATABİLİRSİN (bu dal senin), main'e push ETME, merge ETME.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Her komutun rc'si + ham çıktının son 15 satırı.
Ölçemediğin ekseni `OLCULEMEDI` + sebep. Ürettiğin geçici dosyayı SEN sil; worktree ve ana
ağaç `git status --short` çıktılarını **AYRI AYRI ve ETİKETLİ** bas.
