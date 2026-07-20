# Arşiv — emekli platform araçları

******** / Cults3D / MyMiniFactory KALICI EMEKLİ (commit `4fd279f0`, Okan 19 Tem): arama+ekleme
kapalı, aktif kaynaklar yalnız Thingiverse/Printables/MakerWorld. Bu klasördeki dosyalar (cgt-*,
cults3d-*, myminifactory-*, mmf-pagination-test.py) o platformlara ait ölü kod — SİLİNMEDİ, yalnız
kökten taşındı (yanlış dosya açma maliyetini azaltmak için); içerik bayt-bayt aynı.

`cgt-ekle.py`, `cults3d-api.py`, `myminifactory-api.py` burada DEĞİL — aktif kod hâlâ onlara
referans veriyor (`denetim-kapisi.py`, `gorsel-cakisma-onar.py`, `gorsel-anahtar-test.py`) →
`tools/` kökünde kaldılar.

Geri alma: `git mv tools/arsiv/<dosya> tools/<dosya>`.
