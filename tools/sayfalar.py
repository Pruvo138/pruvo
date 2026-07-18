# -*- coding: utf-8 -*-
"""
PRUVO statik içerik/yasal sayfaları + ödeme logoları.
build.py bu modülü import eder ve her sayfayı /<slug>/index.html olarak üretir.

NOT: Yasal metinler standart e-ticaret şablonudur; satıcı bilgileri gerçek
mükellefiyete göre doldurulmuştur. Yayına almadan mali müşavir/avukata
kontrol ettirmek önerilir.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filament_ortak

# ------------------------------------------------------------------ satıcı bilgileri
SELLER = {
    "unvan": "Okan Gemalmaz",
    "tur": "Şahıs firması",
    "adres": "Akarca Mah. Adnan Menderes (BBT) Blv. No:303 Daire No:203, Fethiye / Muğla",
    "vd": "Fethiye Vergi Dairesi",
    "vkn": "3910052435",
    "tel": "+90 532 595 4005",
    "eposta": "info@pruvo3d.com",
    "kargo": "Yurtiçi Kargo",
    "teslim": "5-7 iş günü",
    "site": "https://pruvo3d.com",
}

# ------------------------------------------------------------------ kişisel veri koruması
# Satıcının kişisel bilgileri (ad, adres, vergi no, telefon, e-posta) HTML kaynağına
# düz metin yazılmaz: değer 2-3 karakterlik parçalara bölünüp data-özniteliklerine
# KARIŞIK SIRADA konur. Görünürlük iki yoldan sağlanır (yasal zorunluluk — müşteri
# her koşulda okuyabilmeli):
#   1) JS açık: sayfadaki küçük betik (PV_SCRIPT_HTML) parçaları doğru sırada
#      birleştirip gerçek metin olarak basar, tel:/mailto:/harita linklerini kurar.
#   2) JS kapalı: CSS `content: attr(data-a) attr(data-b) ...` aynı parçaları doğru
#      sırada ::after içinde gösterir (saf CSS, betik gerekmez). Pseudo-element metni
#      zaten seçilip kopyalanamaz. (Karakter tersleme BİLEREK yok: CSS attr() ters
#      çeviremez; JS'siz görünürlük parçalama+sıra karıştırmayla korunur.)
# Ek katmanlar: .pv-blok üzerinde user-select:none + contextmenu engeli (sadece bu
# bloklarda; sayfanın kalanında sağ tık normal).
_PV_ADLAR = "abcdefghijkl"


def _pv_esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _pv_span(deger):
    # tek span en fazla 12 parça taşır (ilk parça 2, kalanlar 3 karakter = 35 krk.)
    parcalar = []
    i = 0
    while i < len(deger):
        boy = 2 if i == 0 else 3
        parcalar.append(deger[i:i + boy])
        i += boy
    # kaynak sırası karıştırılır: önce tek indisler, sonra çiftler → ardışık iki
    # parça kaynakta yan yana gelmez, ham HTML grep'i/regex hasadı tutmaz.
    sira = list(range(1, len(parcalar), 2)) + list(range(0, len(parcalar), 2))
    attrs = " ".join('data-%s="%s"' % (_PV_ADLAR[j], _pv_esc(parcalar[j]))
                     for j in sira)
    return '<span class="pv pv-blok" %s></span>' % attrs


def pv_html(deger):
    """Kişisel veri değerini kaynakta düz metin bırakmayan korumalı span(lar)."""
    maks = 2 + 3 * (len(_PV_ADLAR) - 1)  # 35 karakter/span
    return "".join(_pv_span(deger[i:i + maks])
                   for i in range(0, len(deger), maks))


# İçerik sayfalarının CSS'ine eklenir (CONTENT_CSS'in sonunda). Statik sayfalar
# (iletisim/gizlilik) aynı kuralları kendi <style> bloklarında taşır.
PV_CSS = """
  .pv::after{content:attr(data-a) attr(data-b) attr(data-c) attr(data-d) attr(data-e) attr(data-f) attr(data-g) attr(data-h) attr(data-i) attr(data-j) attr(data-k) attr(data-l)}
  .pv.pv-tamam::after{content:none}
  .pv-blok{-webkit-user-select:none;-moz-user-select:none;user-select:none}
"""

# İçerik sayfalarının sonuna basılan betik (saf JS, harici kütüphane YOK).
# Statik sayfalarda (iletisim/gizlilik) birebir aynısı gömülü durur.
PV_SCRIPT_HTML = """<script>
// Kişisel veri koruması: parçalanmış data-özniteliklerini birleştirip gösterir,
// tel/e-posta/harita linklerini kurar, korumalı bloklarda sağ tıkı kapatır.
(function(){
  var K="abcdefghijkl";
  var sp=document.querySelectorAll(".pv");
  for(var i=0;i<sp.length;i++){
    var v="";
    for(var j=0;j<K.length;j++){ v+=sp[i].getAttribute("data-"+K[j])||""; }
    sp[i].textContent=v;
    sp[i].className+=" pv-tamam";
  }
  var ln=document.querySelectorAll("[data-pv-link]");
  for(var m=0;m<ln.length;m++){
    var a=ln[m], ic=a.querySelectorAll(".pv"), t=a.getAttribute("data-pv-link"), d="";
    for(var n=0;n<ic.length;n++){ d+=ic[n].textContent; }
    if(t==="tel"){ a.href="tel:"+d.replace(/[^+0-9]/g,""); }
    else if(t==="eposta"){ a.href="mailto:"+d; }
    else if(t==="harita"){ a.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(d); }
  }
  var bl=document.querySelectorAll(".pv-blok");
  for(var b=0;b<bl.length;b++){
    bl[b].addEventListener("contextmenu",function(e){e.preventDefault();});
  }
})();
</script>"""

# ------------------------------------------------------------------ ödeme logoları (footer)
# Güvenli, her zaman render olan inline SVG rozetler. iyzico resmi "logo band"
# varsa panelden alıp değiştirilebilir.
PAY_BAND_HTML = """<div class="pay-band">
  <span class="pay-label">Güvenli Ödeme</span>
  <span class="pay-logos">
    <span class="pay-pill pay-iyzico">iyzico<b>&nbsp;ile Öde</b></span>
    <span class="pay-pill"><svg viewBox="0 0 48 16" width="46" height="15" role="img" aria-label="Visa"><text x="24" y="13" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" font-style="italic" font-weight="700" fill="#1a1f71">VISA</text></svg></span>
    <span class="pay-pill"><svg viewBox="0 0 40 24" width="38" height="23" role="img" aria-label="Mastercard"><circle cx="15" cy="12" r="9" fill="#EB001B"/><circle cx="25" cy="12" r="9" fill="#F79E1B"/><path d="M20 5.2a9 9 0 0 0 0 13.6 9 9 0 0 0 0-13.6z" fill="#FF5F00"/></svg></span>
  </span>
</div>"""

# footer alt navigasyon (yasal + kurumsal linkler)
FOOT_NAV_HTML = (
    '<div class="foot-nav">'
    '<a href="/hakkimizda/">Hakkımızda</a> &middot; '
    '<a href="/iletisim/">İletişim</a> &middot; '
    '<a href="/sss/">S.S.S.</a> &middot; '
    '<a href="/malzeme-rehberi/">Malzeme Rehberi</a> &middot; '
    '<a href="/gizlilik/">Gizlilik Politikası</a> &middot; '
    '<a href="/teslimat-iade/">Teslimat ve İade</a> &middot; '
    '<a href="/mesafeli-satis/">Mesafeli Satış Sözleşmesi</a>'
    '</div>'
)

# ------------------------------------------------------------------ içerik sayfaları için ek CSS
CONTENT_CSS = """
  .content{max-width:820px;margin:0 auto;padding:34px 20px 56px}
  .content h1{font-size:26px;color:var(--navy);margin:0 0 6px}
  .content .lead{color:var(--gray-text);font-size:14px;margin-bottom:26px}
  .content h2{font-size:18px;color:var(--navy);margin:28px 0 10px}
  .content p,.content li{font-size:15px;color:#39434f;line-height:1.75}
  .content ul,.content ol{padding-left:20px;margin:8px 0}
  .content a{color:var(--navy-2)}
  .content .info-table{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:14.5px}
  .content .info-table td{padding:8px 10px;border:1px solid var(--gray-line);vertical-align:top}
  .content .info-table td:first-child{background:var(--gray-card);font-weight:600;color:var(--navy);width:38%}
  .content .info-table th{padding:8px 10px;border:1px solid var(--gray-line);background:var(--navy);
    color:#fff;text-align:left;font-size:13.5px}
  .content .karsilastirma td:first-child{width:auto;white-space:nowrap}
  .content .upd{margin-top:30px;font-size:12.5px;color:var(--gray-text)}
  .pay-band{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:14px}
  .pay-label{font-size:12px;color:#8996ad;letter-spacing:.4px}
  .pay-logos{display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap}
  .pay-pill{display:inline-flex;align-items:center;background:#fff;border-radius:6px;
    padding:5px 9px;height:26px;box-shadow:0 1px 3px rgba(0,0,0,.18)}
  .pay-iyzico{font-weight:800;font-size:13px;color:#1e64ff;letter-spacing:-.3px}
  .pay-iyzico b{color:#12294d;font-weight:700}
""" + PV_CSS


def _seller_table():
    # Kişisel değerler düz metin basılmaz — pv_html (yukarıdaki koruma katmanı).
    s = SELLER
    return (
        '<table class="info-table pv-blok"><tbody>'
        '<tr><td>Satıcı</td><td>%s (%s)</td></tr>'
        '<tr><td>Adres</td><td>%s</td></tr>'
        '<tr><td>Vergi Dairesi / No</td><td>%s &ndash; %s</td></tr>'
        '<tr><td>Telefon</td><td>%s</td></tr>'
        '<tr><td>E-posta</td><td>%s</td></tr>'
        '<tr><td>Web</td><td>pruvo3d.com</td></tr>'
        '</tbody></table>'
        % (pv_html(s["unvan"]), s["tur"], pv_html(s["adres"]),
           pv_html(s["vd"]), pv_html(s["vkn"]),
           pv_html(s["tel"]), pv_html(s["eposta"]))
    )


# ------------------------------------------------------------------ sayfa gövdeleri
def _hakkimizda():
    return (
        "<h1>Hakkımızda</h1>"
        '<p class="lead">Ölçüye özel tasarım üretim atölyesi; Türkiye geneli üretip gönderiyoruz.</p>'
        "<p>PRUVO, tekne/marin, otomobil, motosiklet, ev ve endüstriyel cihazlar için "
        "<strong>özel tasarım üretimle yedek parça</strong> ve kişiye özel ürünler üretir. "
        "Piyasada bulunamayan, kırılan ya da aşınan bir parçanın birebir yedeğini çıkarır; "
        "ölçüye özel parçalar ve dekoratif/hobi ürünleri hazırlar.</p>"
        "<p>Amacımız; doğru malzeme ve hassas ölçüyle, ihtiyacınıza tam uyan parçayı "
        "üretip güvenle adresinize ulaştırmaktır.</p>"
        "<h2>Satıcı Bilgileri</h2>" + _seller_table()
    )


def _iletisim():
    s = SELLER
    return (
        "<h1>İletişim</h1>"
        '<p class="lead">Siparişler ve sorularınız için bize ulaşın.</p>'
        "<p>Sipariş ve bilgi almak için en hızlı yol WhatsApp'tır. "
        "Mesai saatleri içinde en kısa sürede dönüş yapıyoruz.</p>"
        '<h2>Bize Ulaşın</h2>'
        '<p><strong>WhatsApp / Telefon:</strong> %s<br>'
        '<strong>E-posta:</strong> %s<br>'
        '<strong>Adres:</strong> %s</p>'
        '<p><strong>Çalışma saatleri:</strong> Pazartesi&ndash;Cumartesi 09:00&ndash;18:00 '
        '(Pazar kapalı).</p>'
        "<h2>Satıcı Bilgileri</h2>" % (s["tel"], s["eposta"], s["adres"])
        + _seller_table()
    )


def _sss():
    return (
        "<h1>Sıkça Sorulan Sorular</h1>"
        '<p class="lead">Sipariş, üretim, kargo ve iade hakkında merak edilenler.</p>'
        "<h2>Nasıl sipariş verebilirim?</h2>"
        "<p>Ürün sayfasındaki <em>Sipariş Ver</em> butonuyla WhatsApp üzerinden bize "
        "ulaşırsınız. İhtiyacınızı netleştirip ölçü/renk gibi detayları aldıktan sonra "
        "üretim ve teslimat sürecini birlikte planlarız.</p>"
        "<h2>Ürünler nasıl üretiliyor?</h2>"
        "<p>Ürünler talep üzerine, ölçüye/isteğe özel olarak üretilir. Kullanım yerine göre "
        "uygun ve dayanıklı malzeme öneririz.</p>"
        "<h2>Teslimat ne kadar sürer?</h2>"
        "<p>Üretim + kargo süresi ürüne göre değişmekle birlikte genellikle "
        "<strong>%s</strong> içindedir. Kargo: %s.</p>"
        "<h2>İade / değişim yapabilir miyim?</h2>"
        "<p>Standart ürünlerde teslim tarihinden itibaren 14 gün içinde cayma hakkınız "
        "vardır. Kişiye/ölçüye özel üretilen ürünlerde mevzuat gereği cayma hakkı "
        "istisnaları geçerli olabilir; ayrıntılar için "
        '<a href="/teslimat-iade/">Teslimat ve İade</a> sayfamıza bakın.</p>'
        "<h2>Ödeme nasıl yapılıyor?</h2>"
        "<p>Sipariş detayları netleştikten sonra ödeme adımları tarafınıza iletilir. "
        "Ödemeleriniz güvenli altyapı üzerinden alınır.</p>"
        % (SELLER["teslim"], SELLER["kargo"])
    )


def _gizlilik():
    s = SELLER
    return (
        "<h1>Gizlilik Politikası ve KVKK Aydınlatma Metni</h1>"
        '<p class="lead">Kişisel verilerinizin korunması bizim için önemlidir.</p>'
        "<p>Bu politika, %s (\"Satıcı\") tarafından pruvo3d.com üzerinden toplanan kişisel "
        "verilerin 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) kapsamında nasıl "
        "işlendiğini açıklar. Veri sorumlusu Satıcı'dır.</p>"
        "<h2>Toplanan Veriler</h2>"
        "<ul><li>Ad-soyad, telefon, e-posta ve teslimat adresi (sipariş için).</li>"
        "<li>Sipariş ve iletişim içeriği.</li>"
        "<li>Site kullanımına dair teknik veriler (çerezler aracılığıyla, aşağıya bkz.).</li></ul>"
        "<h2>İşleme Amaçları</h2>"
        "<ul><li>Siparişin alınması, üretilmesi, teslimi ve faturalandırılması.</li>"
        "<li>Müşteri iletişimi ve destek.</li>"
        "<li>Yasal yükümlülüklerin yerine getirilmesi.</li></ul>"
        "<h2>Aktarım</h2>"
        "<p>Verileriniz yalnızca hizmetin gerektirdiği ölçüde; kargo firması ve ödeme "
        "kuruluşu gibi iş ortaklarıyla ve yetkili kamu kurumlarıyla paylaşılabilir. "
        "Üçüncü kişilere pazarlama amacıyla satılmaz.</p>"
        "<h2>Ödeme Güvenliği</h2>"
        "<p>Kart bilgileriniz Satıcı tarafından saklanmaz; ödemeler lisanslı ödeme "
        "kuruluşunun güvenli altyapısı üzerinden işlenir.</p>"
        "<h2>Çerezler</h2>"
        "<p>Sitenin düzgün çalışması ve deneyiminizin iyileştirilmesi için çerezler "
        "kullanılabilir. Tarayıcı ayarlarından çerezleri yönetebilirsiniz.</p>"
        "<h2>Haklarınız (KVKK m.11)</h2>"
        "<p>Kişisel verilerinize erişme, düzeltilmesini/silinmesini isteme ve işlemeye "
        "itiraz etme haklarına sahipsiniz. Talepleriniz için: %s</p>"
        "<h2>İletişim</h2>" + _seller_table()
    ) % (s["unvan"], s["eposta"])


def _teslimat_iade():
    s = SELLER
    return (
        "<h1>Teslimat ve İade Koşulları</h1>"
        '<p class="lead">Kargo, teslimat süresi ve iade/cayma hakkı.</p>'
        "<h2>Teslimat</h2>"
        "<ul>"
        "<li>Ürünler talep üzerine üretildiğinden teslim süresi üretim + kargo süresini "
        "kapsar; genellikle <strong>%s</strong> içindedir. Özel/karmaşık işlerde süre "
        "sipariş sırasında bildirilir.</li>"
        # Kargo metni ACIK KURAL olarak yazilir (mimar karari, 16 Tem; Okan kurali —
        # tutarlar secenekler.js kargoKurus ile birebir, degisirse burasi da guncellenir).
        "<li>Gönderiler <strong>%s</strong> ile yapılır. 2.500 TL altındaki siparişlerde "
        "kargo ücreti 250 TL'dir; 2.500 TL ve üzeri siparişlerde kargo ücretsizdir.</li>"
        "<li>Teslimatta pakedi kontrol edin; hasarlıysa tutanak tutturup teslim almayın "
        "ve bizimle iletişime geçin.</li>"
        "</ul>"
        "<h2>Cayma Hakkı ve İade</h2>"
        "<ul>"
        "<li>Standart (stok/seri) ürünlerde, teslim tarihinden itibaren <strong>14 gün</strong> "
        "içinde gerekçe göstermeden cayma hakkınız vardır.</li>"
        "<li>Cayma bildirimini %s adresinden ya da %s numarasından iletin. Ürünü kullanılmamış "
        "ve tekrar satılabilir durumda iade edin.</li>"
        "<li>İade onayından sonra bedel, ödeme yönteminize 14 gün içinde iade edilir.</li>"
        "</ul>"
        "<h2>Cayma Hakkının İstisnası</h2>"
        "<p>Mesafeli Sözleşmeler Yönetmeliği m.15 uyarınca <strong>kişiye/ölçüye özel "
        "üretilen, müşteri talepleri doğrultusunda hazırlanan ürünlerde</strong> cayma "
        "hakkı kullanılamaz. Bu ürünler açıkça özel üretim olarak sipariş edilir. Ayıplı "
        "(kusurlu) ürün elbette ücretsiz onarılır ya da değiştirilir.</p>"
        "<h2>Ayıplı / Yanlış Ürün</h2>"
        "<p>Hatalı, hasarlı ya da siparişten farklı bir ürün ulaşırsa; fotoğrafla birlikte "
        "bize ulaşın, kargo masrafı bize ait olacak şekilde değişim/iade sağlarız.</p>"
        "<h2>İletişim</h2>" + _seller_table()
    ) % (s["teslim"], s["kargo"], pv_html(s["eposta"]), pv_html(s["tel"]))


def _mesafeli_satis():
    s = SELLER
    return (
        "<h1>Mesafeli Satış Sözleşmesi</h1>"
        '<p class="lead">İşbu sözleşme, 6502 sayılı Tüketicinin Korunması Hakkında Kanun ve '
        'Mesafeli Sözleşmeler Yönetmeliği uyarınca düzenlenmiştir.</p>'
        "<h2>1. Taraflar</h2>"
        "<p><strong>SATICI:</strong></p>" + _seller_table() +
        "<p><strong>ALICI:</strong> Sipariş sırasında bildirilen ad-soyad, adres ve "
        "iletişim bilgilerine sahip müşteri.</p>"
        "<h2>2. Konu</h2>"
        "<p>İşbu sözleşmenin konusu, ALICI'nın pruvo3d.com üzerinden siparişini verdiği, "
        "nitelikleri ve satış fiyatı sipariş sırasında belirtilen ürünün satışı ve teslimi "
        "ile tarafların hak ve yükümlülüklerinin belirlenmesidir.</p>"
        "<h2>3. Ürün ve Ödeme</h2>"
        "<p>Ürünün türü, miktarı, özellikleri ve tüm vergiler dâhil satış fiyatı sipariş "
        "onayında belirtilir. Ödeme, Satıcı'nın sunduğu güvenli ödeme yöntemleriyle yapılır; "
        "kart bilgileri Satıcı tarafından saklanmaz.</p>"
        "<h2>4. Teslimat</h2>"
        "<p>Ürün, üretim tamamlandıktan sonra <strong>%s</strong> ile ALICI'nın bildirdiği "
        "adrese gönderilir. Teslim süresi genellikle <strong>%s</strong> olup özel üretimlerde "
        "sipariş sırasında bildirilir; yasal azami süre 30 gündür.</p>"
        "<h2>5. Cayma Hakkı</h2>"
        "<p>ALICI, standart ürünlerde teslim tarihinden itibaren <strong>14 gün</strong> içinde "
        "gerekçe göstermeksizin cayma hakkına sahiptir. Cayma bildirimi %s / %s üzerinden "
        "yapılır; ürün kullanılmamış ve tekrar satılabilir olmalıdır. Bedel 14 gün içinde iade "
        "edilir.</p>"
        "<h2>6. Cayma Hakkının İstisnaları</h2>"
        "<p>Yönetmelik m.15 gereği <strong>ALICI'nın istekleri doğrultusunda kişiye/ölçüye "
        "özel hazırlanan ürünlerde</strong> cayma hakkı kullanılamaz. Bu ürünler sipariş "
        "sırasında açıkça özel üretim olarak teyit edilir.</p>"
        "<h2>7. Genel Hükümler</h2>"
        "<p>ALICI, ürün nitelikleri ve satış fiyatını okuyup bilgi sahibi olduğunu ve "
        "elektronik ortamda siparişi onayladığını kabul eder. Ayıplı üründe ALICI'nın "
        "6502 sayılı Kanun'dan doğan hakları saklıdır.</p>"
        "<h2>8. Uyuşmazlık</h2>"
        "<p>İşbu sözleşmeden doğan uyuşmazlıklarda, Ticaret Bakanlığı'nca ilan edilen "
        "değerlere kadar Tüketici Hakem Heyetleri, aşan uyuşmazlıklarda Tüketici Mahkemeleri "
        "yetkilidir.</p>"
        "<p class=\"upd\">Sipariş onayıyla işbu sözleşme kurulmuş sayılır.</p>"
    ) % (s["kargo"], s["teslim"], pv_html(s["eposta"]), pv_html(s["tel"]))


def _malzeme_rehberi():
    """/malzeme-rehberi/ — sitede satılan 4 malzeme (PLA/PETG/ASA/TPU) tam açıklama +
    karşılaştırma tablosu; ayrıca mühendislik malzemeleri (ABS, Karbon Katkılı — WhatsApp
    özel talebiyle) ayrı bölümde, SİTE SEÇENEĞİ OLARAK SUNULMADAN anlatılır (Okan, 16 Tem).
    İçerik tools/filamentler.json'dan üretilir (tek kaynak; ürün sayfası balonlarıyla
    birebir aynı metinler). Isı değeri verilirken ölçüt adı anılır (HDT @ 0.45 MPa)."""
    ref = filament_ortak.referans()
    site_fil = [f for f in ref["filamentler"] if f.get("site")]
    ozel_fil = [f for f in ref["filamentler"] if not f.get("site")]

    def _esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _bolum(f):
        return (
            "<h2>%s — %s</h2>"
            '<p><strong>Isı dayanımı (HDT @ 0.45 MPa):</strong> %s%s</p>'
            "<p>%s</p>"
            % (_esc(f.get("uzunAd") or f["ad"]), _esc(f["kisaEtiket"]),
               _esc(f["isiDayanimi"]),
               (" (%s)" % _esc(f["isiDetay"])) if f.get("isiDetay") else "",
               _esc(f["uzun"])))

    bolumler = "".join(_bolum(f) for f in site_fil)
    ozel_bolumler = "".join(_bolum(f) for f in ozel_fil)

    def _satir(f):
        return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                % (_esc(f["ad"]), _esc(f["isiDayanimi"]), _esc(f["uv"]),
                   _esc(f["su"]), _esc(f["darbe"])))

    tablo = (
        '<div style="overflow-x:auto"><table class="info-table karsilastirma"><thead>'
        "<tr><th>Malzeme</th><th>Isı dayanımı*</th><th>Güneş (UV)</th>"
        "<th>Su / nem</th><th>Darbe</th></tr></thead><tbody>"
        + "".join(_satir(f) for f in site_fil) + "</tbody></table></div>"
        '<p class="upd">* Isı dayanımı ölçütü: HDT @ 0.45 MPa; değerler marka bağımsız '
        "yaklaşık aralıklardır.</p>")

    # Kategori -> varsayılan tavsiye özeti (aynı listeyi paylaşan kategoriler gruplanır)
    gruplar, sira = {}, []
    for kat, liste in ref["kategoriTavsiye"].items():
        anahtar = json.dumps(liste, ensure_ascii=False)
        if anahtar not in gruplar:
            gruplar[anahtar] = []
            sira.append(anahtar)
        gruplar[anahtar].append(kat)
    oneri_md = []
    for anahtar in sira:
        liste = json.loads(anahtar)
        parca = liste[0]["ad"]
        for t in liste[1:]:
            parca += ", %s (%s)" % (t["ad"], t.get("not", "").lower() or "alternatif")
        oneri_md.append("<li><strong>%s:</strong> %s</li>"
                        % (_esc(", ".join(gruplar[anahtar])), _esc(parca)))

    wa = ("https://wa.me/905451386526?text=Merhaba%2C%20m%C3%BChendislik%20malzemesiyle%20"
          "%C3%B6zel%20%C3%BCretim%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum.")

    return (
        "<h1>Malzeme Rehberi</h1>"
        '<p class="lead">Hangi malzeme nerede kullanılır? Dürüst değerler, net öneriler.</p>'
        "<p>Her parçayı kullanım yerine göre uygun malzemeyle üretiyoruz. Aşağıda "
        "sitede sipariş edebileceğiniz dört malzeme sınıfının özelliklerini ve hangi "
        "parçada hangisini önerdiğimizi bulabilirsiniz. Emin değilseniz WhatsApp'tan "
        "sorun; kullanım alanınıza göre birlikte seçelim.</p>"
        + bolumler +
        "<h2>Karşılaştırma</h2>" + tablo +
        "<h2>Hangi parçada hangi malzeme?</h2><ul>" + "".join(oneri_md) + "</ul>"
        "<h2>Mühendislik malzemeleri (özel talep)</h2>"
        '<p>Daha yüksek ısı dayanımı ya da mukavemet gereken kritik parçalar için '
        'ABS ve karbon fiber katkılı malzemeleri <strong>WhatsApp üzerinden özel talep</strong> '
        "olarak değerlendiriyoruz; bu malzemeler standart sipariş akışında (sepet) yer almaz, "
        "kullanım koşullarınızı konuşarak fiyatlandırırız. Karbon katkı ısı dayanımını "
        "artırmaz, taşıyıcı malzemenin değerini korur; katkının kazandırdığı sertlik ve "
        "mukavemettir.</p>"
        + ozel_bolumler +
        '<p><a href="%s" target="_blank" rel="noopener">WhatsApp\'tan mühendislik '
        "malzemesi hakkında bilgi alın &rarr;</a></p>"
        "<p>Ölçüye özel üretilen parçalarda en uygun malzemeyi kullanım alanınıza göre "
        "size sorarak belirleriz.</p>") % _esc(wa)


def _numuneye_gore_plastik_parca_uretimi():
    return (
        "<h1>Numuneye Göre Plastik Parça Üretimi — Getir, Ölçelim, Üretelim</h1>"
        '<p class="lead">Kırılan ya da bulunamayan parçanızı getirin; ölçüsünü alıp ölçüye '
        "özel, doğru malzemeyle üretelim. Tek adet olur.</p>"
        "<h2>Elinizdeki parça kırıldı ya da hiçbir yerde bulunamıyor mu?</h2>"
        "<p>Bazı parçalar artık üretilmez, yedeği kalmaz ya da hiçbir zaman ayrı satılmaz. "
        "Makinenin küçük bir dişlisi, beyaz eşyanın klipsi, teknedeki bir bağlantı aparatı, "
        "eski bir cihazın kırılan tutamağı… Tek bir parça yüzünden koca bir ürün çalışmaz "
        "hale gelir. Piyasada muadili yoktur, kalıpçıya gitseniz tek adet için kalıp masrafı "
        "anlamsızdır.</p>"
        "<p>İşte tam bu noktada devreye giriyoruz: <strong>elinizdeki numuneye göre, ölçüye "
        "özel plastik parça üretiyoruz.</strong> Bir tane bile olsa üretiriz.</p>"
        "<h2>Nasıl çalışır: getir, ölçelim, üretelim</h2>"
        "<ol><li><strong>Getir</strong> — Kırık parçayı, eski numuneyi ya da yerine geçecek "
        "örneği bize ulaştırın. Elinizde parça yoksa ölçü ve fotoğraf da çoğu zaman yeterli olur.</li>"
        "<li><strong>Ölçelim</strong> — Parçanın milimetrik ölçüsünü çıkarır, kırık ya da "
        "aşınmış yerleri tamamlayarak orijinaline sadık kalırız.</li>"
        "<li><strong>Üretelim</strong> — Ölçüye özel üretir, kullanacağınız yere uygun "
        "malzemeyle teslim ederiz.</li></ol>"
        "<p>Ölçü sizden, üretim bizden. Standart kataloglara sığmayan işin adresi burası.</p>"
        "<h2>Sadece ölçü değil, doğru malzeme</h2>"
        "<p>Bir parçanın dayanması yalnızca ölçüsüne değil, doğru malzemeye de bağlıdır. "
        "İşi olacağı yere göre malzeme merdiveninde konumlandırırız:</p>"
        "<ul><li><strong>Standart iç mekân kullanımı</strong> için ekonomik ve boyutsal "
        "olarak stabil seçenekler.</li>"
        "<li><strong>Isı, güneş (UV) ve dış/deniz koşulu</strong> görecek parçalar için "
        "PETG, ASA veya PC gibi dayanıklı malzemeler.</li>"
        "<li><strong>Yüksek mukavemet</strong> isteyen, yük altında çalışacak parçalar için "
        "karbon ya da cam elyaf takviyeli PA-CF / PA-GF.</li></ul>"
        "<p>Ayrıca farklı renk seçenekleriyle üretim mümkün. Parçanızı anlatın, hangi "
        "malzemenin doğru olduğunu birlikte belirleyelim.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik üretimin de bir sınırı var, bunu baştan söyleriz: Ürettiğimiz pervane "
        "tipi parçalar fan / hafif çark işini görür, tekne itiş gücü için değildir. Profil "
        "ve kızak tipi parçalar hafif, yük taşımayan uygulamalar içindir. Contalar düşük–orta "
        "basınca uygundur. Parçanız ağır bir mekanik yük taşıyacaksa bunu önceden konuşur, "
        "sizi yanıltmayız.</p>"
        "<h2>Siparişinizi verin</h2>"
        '<p>Numuneye göre tek adet plastik parça üretimi için siteden kartla güvenli ödeme '
        'yapabilir veya parçanızın fotoğrafını ve ölçüsünü WhatsApp üzerinden '
        'gönderebilirsiniz: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        '<p><a href="/">PRUVO ürün ve özel üretim hizmetini</a> inceleyin; benzer çözümler '
        'için <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça</a> '
        've <a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçası</a> '
        "sayfalarına bakın.</p>"
        "<p>Bulunamayan parça diye bir dert kalmasın. Getirin, ölçelim, üretelim.</p>"
    )


def _bulunamayan_yedek_parca_ozel_uretim():
    return (
        "<h1>Bulunamayan Yedek Parça İçin Özel Üretim</h1>"
        '<p class="lead">Servis “parça yok” mu dedi? Üretimi durmuş ya da piyasada olmayan '
        "parçayı ölçüsüne göre özel üretiyoruz.</p>"
        '<h2>"Parça yok" duvarına mı çarptınız?</h2>'
        "<p>Cihaz sağlam, tek bir parça kırık. Ama yetkili servis “o parça artık gelmiyor” "
        "diyor, model üretimden kalkmış, piyasada da bulunamıyor. <strong>Yetkili servis parça "
        "yok dediğinde ne yapabilirim</strong> sorusunun cevabı çoğu zaman koca bir makineyi "
        "hurdaya çıkarmak zorunda olmadığınız: kırılan, aşınan ya da kaybolan o küçük parçayı "
        "ölçüsüne göre yeniden ürettirebilirsiniz.</p>"
        "<p>PRUVO tam da bunu yapar. <strong>Bulunamayan yedek parça özel üretim</strong> ve "
        "<strong>üretimi durmuş parça yaptırma</strong> işimizin merkezinde: kataloğu olmayan, "
        "tedariki kesilmiş ya da hiç seri üretilmemiş parçaları tek adet halinde üretiriz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Süreç sade. <strong>Getirirsiniz</strong> — elinizdeki kırık parçayı, eski parçanın "
        "fotoğrafını ya da yerine oturması gereken boşluğun ölçülerini paylaşırsınız. "
        "<strong>Ölçeriz</strong> — parçanın geometrisini, delik yerlerini, kalınlığını ve "
        "montaj noktalarını birebir çıkarırız. <strong>Üretiriz</strong> — ölçüye özel, tek "
        "parça olarak üretip elinize teslim ederiz.</p>"
        "<p>Elinizde numune olması şart değil; ölçüler, montaj deliği aralıkları ve fotoğraf "
        "çoğu zaman yeterli. Kırık parçanın iki yarısı varsa daha da net sonuç alırsınız.</p>"
        "<h2>Ölçüye göre neyi ayarlıyoruz</h2>"
        "<p>Seri üründe olmayan esneklik bizde standart. Parçanın <strong>dış ölçülerini</strong> "
        "birebir hedefe göre ayarlıyoruz; <strong>montaj/vida deliklerinin yerini ve "
        "aralığını</strong> eşleştiriyoruz; klips, tırnak, geçme gibi <strong>bağlantı "
        "detaylarını</strong> yerine oturacak şekilde işliyoruz; kalınlık ve et payını "
        "dayanıklılığa göre belirliyoruz. Renk tarafında <strong>farklı renk seçenekleri</strong> "
        "sunuyoruz. Yani “yaklaşık benzeri” değil, boşluğa tam oturan parça.</p>"
        "<h2>Doğru malzeme, kalıcı çözüm</h2>"
        "<p>İç mekân ve düşük yük parçalarında ekonomik seçenekler yeterlidir; ısı, güneş "
        "(UV), nem ve deniz koşullarında PETG, ASA veya PC gibi dayanıklı malzemelere çıkarız; "
        "taşıyıcı ve yüksek mukavemet gereken parçalarda karbon ya da cam fiber takviyeli "
        "PA-CF / PA-GF kullanırız. Parçanın nerede çalışacağını sorar, ona göre yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Her şeyi vaat etmeyiz; güven buradan gelir. Özel üretim parça, tekne iten bir "
        "pervane ya da ağır yük "
        "taşıyan ana bir kiriş değildir; pervane tipi işlerde fan/hafif çark, profillerde "
        "yük-dışı/hafif kullanım, contalarda düşük–orta basınç mantıklıdır. Ağır zorlanmayı "
        "baştan değerlendirip doğru malzemeye ya da uygun tasarıma yönlendiririz.</p>"
        "<h2>Siparişe başlayın</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a> inceleyebilir; '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimi</a> '
        've <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası üretimi</a> '
        "hakkında ayrıntı okuyabilirsiniz.</p>"
        '<p>Ölçüye özel üretimi sitemizden kartla online sipariş edebilirsiniz. Emin değilseniz '
        'ya da parçanızı önce değerlendirmemizi istiyorsanız fotoğraf ve ölçüyle WhatsApp’tan '
        'yazın: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p><strong>Ölçü sizden, üretim bizden.</strong></p>"
    )


def _beyaz_esya_plastik_parca_uretimi():
    return (
        "<h1>Beyaz Eşya Plastik Parçası Kırıldı? Yenisini Üretelim</h1>"
        '<p class="lead">Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri… Kırılan '
        "beyaz eşya plastiğini ölçüsüne göre üretiyoruz.</p>"
        "<h2>Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri — küçük bir plastik "
        "parça yüzünden cihaz elde kalmasın</h2>"
        "<p>Beyaz eşyalarda en çok kırılan şey koca bir motor değil; küçük bir plastik "
        "parçadır. Buzdolabı kapak rafı, sebzelik rayı, çamaşır makinesi kapak menteşesi, "
        "bulaşık makinesi sepet tekeri, fan kanadı, düğme, tutamak… Servis çoğu zaman o "
        "parçanın tek satılmadığını, komple modülün değişeceğini söyler; modelin yaşı bir-iki "
        "yılı geçtiyse yedeğinin kalmadığını söyler. Oysa çalışmayan tek şey avuç içi kadar "
        "bir parçadır.</p>"
        "<p>Biz o tek parçayı yeniden üretiyoruz. Komple modül almanıza gerek yok.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Akış basit. <strong>Kırık parçayı bize ulaştırın</strong> — elinizdeki numune, "
        "kırık haliyle bile yeter. "
        "Parçadan <strong>ölçüyü alırız</strong>, kırık kısımları tamamlar, ölçüye özel yeniden "
        "<strong>üretiriz</strong>. Numune yoksa ölçülü bir fotoğraf veya cihazın marka-modeli "
        "de çoğu durumda çıkış noktası olur.</p>"
        "<p>Tek adet üretiriz — minimum sipariş yok. Piyasada bulunamayan, üretimi durmuş, "
        "eski model parçalar tam da bizim işimizdir.</p>"
        "<h2>Ölçüye göre ayarladığımız seçenekler</h2>"
        "<p>Parçayı birebir kopyalamakla kalmayız; ihtiyacınıza göre uyarlarız:</p>"
        "<ul><li><strong>Boyut ve delik ölçüleri</strong> — vida deliği aralığı, çap, kalınlık "
        "sizin parçanıza göre.</li>"
        "<li><strong>Bağlantı ve montaj noktaları</strong> — geçme, vidalı, klipsli detaylar.</li>"
        "<li><strong>Dayanım kademesi</strong> — kullanılacağı yere göre malzeme seçimi.</li>"
        "<li><strong>Farklı renk seçenekleri</strong> — cihaza uygun tonlarda.</li></ul>"
        "<h2>Doğru malzeme, uzun ömür</h2>"
        "<p>Beyaz eşyanın içi sıradan plastiği yorar: sıcak, nem ve sürekli yük. Isıya ve "
        "neme dayanıklı PETG / ASA / PC; sürekli zorlanan menteşe ve taşıyıcı parçalarda "
        "cam ya da karbon fiber takviyeli PA-GF / PA-CF ile yüksek mukavemet hedefleriz. "
        "Fırın içi gibi yüksek sıcaklık noktaları malzemenin sınırını aşabilir; orada sizi "
        "baştan doğru yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Her parçayı her koşulda garanti etmeyiz — güveniniz bizim için bir kere satıştan "
        "önemli. Taşıyıcı raf, menteşe, teker, tutamak, düğme ve kanat gibi mekanik parçalarda "
        "doğru malzemeyle uzun ömürlü sonuç alırız. Çok yüksek sıcaklık ya da ağır darbe "
        "alan noktalarda sınırı önceden söyler, en uygun çözümü öneririz.</p>"
        "<h2>Parçanızı üretmeye hazırız</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetine</a> dönün; '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre üretim</a>, '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça</a> ve '
        '<a href="/malzeme-rehberi/">malzeme rehberi</a> sayfalarını inceleyin.</p>'
        '<p>Kırık parçanızın fotoğrafını gönderin, birlikte bakalım. Sitemizden kartla online '
        'sipariş verebilir; ölçü danışmanlığı ve özel işler için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _oto_ic_trim_klips_parca_uretimi():
    return (
        "<h1>Bulunamayan Oto İç Trim ve Klips Parçalarının Üretimi</h1>"
        '<p class="lead">Torpido ızgara klipsi, kapak kolu ve iç trim braketi bulunamıyor '
        "mu? Kırılan parçayı numuneden ölçüye özel üretiyoruz.</p>"
        "<h2>Küçük bir klips yüzünden takılıp kalmayın</h2>"
        "<p>Aracın içindeki en küçük parça bile bir yerde tutar: torpido ızgarasını yerine "
        "oturtan klips, kapak kolunun arkasındaki mandal, tavan döşemesini taşıyan braket, "
        "konsol bağlantı tırnağı. Bu alt parçalar çoğu zaman münferit satılmaz; ya koca bir "
        "modül almanız istenir ya da “artık üretilmiyor” yanıtını alırsınız. Model eskidikçe bulunamayan "
        "oto plastik parça sorunu büyür.</p>"
        "<p>PRUVO tam bu noktada devreye girer. Kırılan, çatlayan veya kaybolan iç trim "
        "parçasını <strong>numuneden ölçüye özel üretiyoruz</strong> — tek adet de olsa.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<ol><li><strong>Getir</strong> — Elinizdeki kırık parçayı, kalıntıyı veya net bir "
        "fotoğrafı/ölçüyü bize iletin. Parça kırıksa iki parçadan da eksiksiz bir bütün "
        "çıkarabiliriz.</li>"
        "<li><strong>Ölç</strong> — Klips çapı, tırnak açısı, geçme mesafesi, vida yuvası gibi "
        "kritik ölçüleri milimetrik çıkarırız. Orijinaline oturması için önemli olan tutuş "
        "noktalarıdır.</li>"
        "<li><strong>Üret</strong> — Onayınızla parçayı üretir, size ulaştırırız.</li></ol>"
        "<p>Torpido ızgara klipsi, kapak kolu mandalı, döşeme braketi, konsol tırnağı ve "
        "hava kanalı yönlendiricisi gibi iç aksam parçalarında çalışırız.</p>"
        "<h2>Doğru malzeme = orijinali kadar dayanıklı</h2>"
        "<p>Her parça aynı plastikten çıkmaz. İç trim parçaları araç içinde ısıya ve UV’ye "
        "maruz kalır; yazın kapalı araçta torpido üstü ciddi ısınır. Bu yüzden malzemeyi "
        "işine göre seçeriz:</p>"
        "<ul><li>Düşük yük, iç mekân görünürde olmayan parça — dengeli, temiz malzeme.</li>"
        "<li><strong>Isı ve UV dayanımı</strong> gereken görünür trim parçalarında PETG / ASA / PC.</li>"
        "<li><strong>Sürekli esneyen ve yüksek mukavemet isteyen</strong> klips ve braketlerde "
        "karbon ya da cam fiber takviyeli PA-CF / PA-GF.</li>"
        "<li>İç döşeme tonuna yakın farklı renk seçenekleri.</li></ul>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik parçanın gücünü olduğu gibi söyleriz. İç trim klipsi ve braketler bu "
        "üretim için çok uygundur — orijinali de plastiktir. "
        "Ancak sürekli darbe alan taşıyıcı bir gövde ya da yüksek sıcaklıktaki motor bölmesi "
        "parçasında koşulları baştan değerlendiririz. Amacımız parçanın çalışacağı yerde tutmasıdır.</p>"
        "<h2>Parçanızı üretelim</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneden parça üretimini</a> ve '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça çözümünü</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Sitemizden kartla online sipariş verebilir; fotoğraf ve ölçü danışmak için '
        'WhatsApp üzerinden yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _makine_parcasi_olcuye_ozel_uretim():
    return (
        "<h1>Makinenizin Bulunamayan Plastik Parçası İçin Ölçüye Özel Üretim</h1>"
        '<p class="lead">Üretimden kalkmış makinenin plastik dişli, kasnak ya da burcu '
        "bulunamıyor mu? Numuneden ölçüye özel üretelim.</p>"
        "<h2>Parça piyasada yok, makine duruyor</h2>"
        "<p>Bir plastik dişli kırıldı, bir kasnak aşındı, bir burç dağıldı; ama parça artık "
        "hiçbir yerde bulunamıyor. Makine üretimden kalkmış, üretici kapanmış, yedek stok "
        "tükenmiş. Elinizde "
        "çalışan koca bir tezgâh var, sırf küçük bir plastik parça yüzünden bekliyor. Sanayide, "
        "atölyede, bakım hattında en çok karşılaşılan tıkanma budur: <strong>parçanın kendisi "
        "değil, bulunamaması</strong> işi durdurur.</p>"
        "<p>PRUVO tam bu noktada devreye girer. Kırılan, aşınan ya da hiç bulunamayan makine "
        "parçasını <strong>ölçüye özel üretiriz</strong>. Katalogdan seçmezsiniz; sizin parçanız, "
        "sizin makineniz için üretilir.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Süreç sade. Kırık parçayı ya da elinizdeki numuneyi bize ulaştırırsınız. Parçayı "
        "<strong>milimetrik olarak ölçeriz</strong>; diş sayısı, çap, kalınlık, montaj deliği "
        "ve geçme toleransı dahil ölçeriz. Numune yoksa teknik çizim, fotoğraf ya da eski "
        "parçanın ölçüleriyle de çalışırız. Ardından <strong>ölçüye özel üretiriz</strong> ve "
        "size ulaştırırız. Bulunamayan bir parçayı yeniden var etmenin en hızlı yolu budur.</p>"
        "<p>Numune ne kadar sağlamsa üretim o kadar birebir olur; parçanız kırık da olsa "
        "çoğu zaman ölçüyü çıkarmaya yeter.</p>"
        "<h2>Doğru malzeme = güven</h2>"
        "<p>Her parça aynı plastikten yapılmaz. Parçanın <strong>çalışacağı koşula göre "
        "malzeme seçeriz</strong>:</p>"
        "<ul><li>Isıya, güneşe ve neme maruz kalan parçalarda PETG, ASA veya PC.</li>"
        "<li>Yük taşıyan, sürtünen ve tork aktaran parçalarda karbon ya da cam fiber "
        "takviyeli PA-CF / PA-GF.</li>"
        "<li>Ölçüye özel üretimde farklı renk seçenekleri.</li></ul>"
        "<p>Böylece parça sadece “boşluğu doldurmaz”, makinenin gerçek çalışma yükü altında "
        "ayakta kalır.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik üretim güçlüdür ama her işin ilacı değildir; size bunu açıkça söyleriz. "
        "Diş profili, kasnak, burç, kılavuz, tampon, muhafaza, tırnak ve konektör gibi "
        "parçalarda iyi sonuç alırız. Ağır darbe alan, sürekli yüksek sıcaklıkta çalışan ya "
        "da metal mukavemeti şart olan parçalarda sınırı baştan söyleriz. Amaç bir defalık "
        "satış değil, çalışan bir parçadır.</p>"
        "<h2>Parçanızı yeniden üretelim</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişliyi</a>, '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">triger kasnağını</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman yatağını</a> '
        "inceleyin.</p>"
        '<p>Siteden kartla online sipariş verebilir; numune, ölçü ve özel iş danışması için '
        'WhatsApp üzerinden ulaşabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Numuneyi getirin, ölçelim, üretelim; makineniz tekrar çalışsın.</p>"
    )


def _tekne_plastik_parca_ozel_uretim_gocek_fethiye():
    return (
        "<h1>Tekne ve Marina Plastik Parçaları — Göcek ve Fethiye'de Ölçüye Özel Üretim</h1>"
        '<p class="lead">Göcek ve Fethiye’de teknenizin kırılan veya bulunamayan plastik '
        "parçasını deniz koşuluna dayanıklı ASA/PETG ile ölçüye özel üretiyoruz.</p>"
        "<p>Teknede bir parça kırılır ve tam o modelin yedeği hiçbir yerde bulunmaz. Eski bir "
        "motor, üretimi durmuş bir aksesuar ya da güneşte kırılganlaşıp çatlayan bir kapak, "
        "klips, menteşe, ızgara… Bayi “artık gelmiyor” der, marinadaki dükkânlarda muadili "
        "yoktur. Göcek ve Fethiye'de teknesiyle uğraşan herkesin tanıdığı bir sorun bu.</p>"
        "<p>PRUVO tam burada devreye girer: <strong>piyasada olmayan, kırılan ya da hiç "
        "bulunamayan plastik parçayı teknenize göre ölçüye özel üretiyoruz.</strong></p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Yol basit. Kırık parçayı ya da eldeki örneği <strong>getirirsiniz</strong>; birebir "
        "<strong>ölçeriz</strong>, kırık da olsa eldeki ölçüden yeniden çıkarırız; teknenize "
        "takılacak yeni parçayı <strong>üretiriz</strong>. Örnek parça yoksa ölçüleri sizden "
        "alır, çizip onayınıza sunarız. Ölçü sizden, üretim bizden.</p>"
        "<p>Ölçüye özel çalıştığımız için biçim, kalınlık, delik yerleri, kenar ve montaj "
        "detayları sizin parçanıza göre ayarlanır — hazır raf ürünü değil, teknenizin "
        "ihtiyacına oturan parça çıkar. Farklı "
        "renk seçenekleriyle de üretilebilir.</p>"
        "<h2>Deniz koşuluna doğru malzeme</h2>"
        "<p>Deniz ortamı plastiğe acımasız: tuz, sürekli güneş, ısı, nem. Sıradan malzeme "
        "(PLA) burada kısa sürede sararır ve kırılganlaşır. Parçayı çalışacağı yere göre doğru "
        "malzemeye yönlendiririz:</p>"
        "<ul><li><strong>PETG / ASA:</strong> UV, ısı ve deniz koşuluna dayanıklı; güverte "
        "üstü ve dış mekân parçalarının çoğu için doğru seçim; özellikle ASA uzun güneş "
        "maruziyetinde renk ve mukavemetini korur.</li>"
        "<li><strong>PC:</strong> daha yüksek ısı ve darbe direnci gereken yerlerde.</li>"
        "<li><strong>PA-CF / PA-GF:</strong> braket, bağlantı ve yüksek mukavemet isteyen "
        "parçalarda karbon ya da cam fiber takviyeli seçenekler.</li></ul>"
        "<p>Hangi parçanın hangi malzemeyle daha uzun dayanacağını birlikte konuşur, size en "
        "uygununu öneririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Bu üretimin sınırını da açıkça söyleriz — güven bundan doğar. Plastik parça; "
        "pervane işi için fan/hafif çark seviyesindedir ve tekneyi iten "
        "sevk pervanesi değildir. Profil ve beam gibi parçalar hafif, yük-dışı kullanım "
        "içindir; conta ise düşük–orta basınçta iş görür. Yani her parçayı üretiriz demeyiz; "
        "parçanızın çalışacağı koşula bakar, o koşulu kaldıracaksa üretir, kaldırmayacaksa "
        "baştan söyleriz.</p>"
        "<h2>Parçanızı üretelim</h2>"
        '<p><a href="/?kategori=Marin">Marin ürünlerini ve ana hizmeti</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimini</a>, '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça çözümünü</a> '
        've <a href="/iletisim/">iletişim bilgilerini</a> inceleyebilirsiniz.</p>'
        '<p>Siteden kartla online sipariş verebilir; parçanızın fotoğrafı ve ölçüsü için '
        'WhatsApp üzerinden danışabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Göcek ve Fethiye'de tekneniz için ölçüye özel plastik parça: ölçü sizden, "
        "üretim bizden.</p>"
    )


def _kisiye_ozel_logolu_kase_yaptirma():
    return (
        "<h1>Kişiye Özel Logolu Kaşe Yaptırma</h1>"
        '<p class="lead">Yazı, logo ya da ikon işlenmiş kaşenizi ölçünüze göre üretiyoruz: '
        "dikdörtgen/kare/yuvarlak, düz veya kesikli çerçeve, vidalı ayrı sap. Online sipariş.</p>"
        "<p>İşletme adınız, logonuz ya da özel bir ikonla kaşe aradığınızda genelde iki "
        "sorunla karşılaşırsınız: hazır kalıplar sizin ölçünüze ve tasarımınıza "
        "uymaz, ya da eldeki kaşenin sapı kırılır, yazısı silinir, yenisini bulmak zorlaşır. "
        "Piyasada tam istediğiniz biçimde bir karşılığı olmayan bu parçayı, siz nasıl "
        "istiyorsanız öyle, ölçüye özel üretiyoruz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Yöntemimiz basit. Bize kaşede olmasını istediğiniz içeriği (yazı, logo, ikon) ve "
        "tercih ettiğiniz biçimi iletirsiniz; biz tasarımı ölçünüze göre kurar, ölçüye özel "
        "üretir, kargoya veririz. Kırılan bir kaşenin ölçüsünü verdiğinizde de birebir "
        "karşılığını çıkarabiliriz. "
        "Hazır rafa bağlı değilsiniz; parça ihtiyacınıza göre şekillenir.</p>"
        "<h2>Ölçünüze göre ayarladığımız seçenekler</h2>"
        "<p>Logolu kaşe yaptırma sürecinde şu ayarları size göre belirliyoruz:</p>"
        "<ul><li><strong>İçerik:</strong> düz yazı, ikon/emoji, yazı ile ikonun birlikte "
        "kullanımı ya da kendi logonuz işlenir.</li>"
        "<li><strong>Biçim:</strong> dikdörtgen, kare veya yuvarlak.</li>"
        "<li><strong>Çerçeve:</strong> çerçevesiz, düz çerçeve veya kesikli çerçeve.</li>"
        "<li><strong>Sap:</strong> ayrı parça olarak vidalı takılan sap; sap kırılırsa "
        "gövdeyi değil yalnız o parçayı yenilersiniz.</li>"
        "<li><strong>Boyut:</strong> içeriğe göre ölçeklenir, kartvizit yazınızdan büyük "
        "logonuza kadar orantılı çıkar.</li>"
        "<li><strong>Renk:</strong> farklı renk seçenekleri arasından belirlersiniz.</li></ul>"
        "<p>Belirsiz “her şeyi yaparız” yerine, gerçek ayarları önünüze koyuyoruz; ne "
        "alacağınızı baştan bilirsiniz.</p>"
        "<h2>Doğru malzeme, uzun ömür</h2>"
        "<p>Kaşe her gün elden geçen bir parçadır; malzemesi işini görmeli. Standart günlük "
        "kullanım için dayanıklı gövde, daha zorlu koşullarda ısıya ve dış etkiye direnç "
        "isteyen kullanım için PETG, ASA veya PC, sürekli yük altındaki yoğun kullanım "
        "için karbon/cam fiber takviyeli PA-CF / PA-GF malzemelere kadar sizi doğru "
        "seçenekle eşleştiririz. Amaç, sapın ve gövdenin ilk "
        "aya değil yıllara dayanmasıdır.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Kaşe, mürekkep aktaracağı yüzeyde net iz bırakmalıdır. Çok ince detayları çok "
        "küçük ölçüye sığdırmaya çalışırsak iz kalitesi düşer. Logonuzun okunur çıkacağı "
        "uygun boyutu birlikte belirler, gerçekçi olmayan sonuç sözü vermeyiz.</p>"
        "<h2>Sipariş</h2>"
        '<p><a href="/">PRUVO ürün ve özel üretim hizmetini</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre özel üretimi</a> ve '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">tek adet parça çözümünü</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Kaşenizi sitemizden kartla online ödeme ile sipariş edebilirsiniz. Logo dosyası '
        'veya özel biçim için WhatsApp: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _olcuye_ozel_conta_uretimi():
    return (
        "<h1>Ölçüye Özel Conta ve O-ring Üretimi</h1>"
        '<p class="lead">Orijinali bulunmayan contayı iç çap ve kesit ölçünüze göre '
        "üretiyoruz. Yuvarlak, kare ve pahlı profil seçenekleri sunuyoruz.</p>"
        "<p>Aradığınız conta piyasada yok mu? Eski makinenin, pompanın, valfin ya da bir "
        "armatürün sızdırmazlık contası kırıldı, sertleşti veya orijinali artık bulunamıyor "
        "olabilir. Standart dışı bir iç çap, alışılmadık bir kesit ya da üretimi bırakılmış "
        "bir parça söz konusu olduğunda tek tek mağaza dolaşmak çoğu zaman sonuç vermez. Biz "
        "tam bu noktada devreye giriyoruz: <strong>orijinali bulunmayan contayı ölçünüze göre özel "
        "üretiyoruz.</strong></p>"
        "<h2>Nasıl çalışır: getirin, ölçelim, üretelim</h2>"
        "<p>Süreç basit. Elinizdeki eski contayı, sızdıran parçayı ya da yalnızca ölçülerini "
        "bize iletirsiniz. Ölçüyü "
        "teyit eder, doğru profili ve malzemeyi birlikte belirler, ardından size özel üretiriz. "
        "Bir örneğiniz yoksa iç çap ve kesit kalınlığı üretim için yeterli olabilir.</p>"
        "<h2>Ölçünüze göre ne ayarlanabilir?</h2>"
        "<p>Conta hazır bir katalog parçası değil; sizin uygulamanıza göre kurgulanır:</p>"
        "<ul><li><strong>Ölçü:</strong> AS568 standart O-ring kodu ile ya da doğrudan verdiğiniz "
        "iç çap + kesit kalınlığıyla üretiriz.</li>"
        "<li><strong>Profil:</strong> yuvarlak (O), kare, pahlı, D-ring veya X-ring — yuvanıza "
        "hangisi oturuyorsa.</li>"
        "<li><strong>Kullanım yeri:</strong> su, yakıt, ısı ya da dış mekân (UV) — nerede "
        "çalışacağı malzeme seçimini belirler.</li>"
        "<li><strong>Esnek yapı:</strong> yuvasına oturan, sıkıştırıldığında görevini gören "
        "esneklikte.</li><li>Farklı renk seçenekleri.</li></ul>"
        "<h2>Doğru malzeme, doğru koşul</h2>"
        "<p>Sızdırmazlıkta malzeme her şeydir. Sıradan bir seçim yerine, contanın maruz "
        "kalacağı koşula göre yükseliriz: ısı, güneş ve nem söz konusuysa PETG, ASA veya PC; "
        "daha yüksek dayanım ve boyut "
        "kararlılığı gereken yerlerde karbon ya da cam fiber takviyeli PA-CF / PA-GF "
        "malzemelere geçeriz. Hangi ortamda çalışacağını bize söylediğinizde, ömrü en uzun "
        "olacak malzemeye yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Şeffaf olalım: özel tasarım üretim conta <strong>düşük–orta basınçlı</strong> "
        "sızdırmazlık için "
        "uygundur; toz, sıvı sızıntısı, titreşim yalıtımı, kapak ve muhafaza contaları gibi. "
        "Yüksek basınçlı hidrolik hatlar ya da ağır yük altındaki sistemler bu üretimin "
        "sınırının dışındadır. Contanızın nerede çalışacağını paylaşırsanız, uygunsa üretir; "
        "değilse baştan söyleriz. Amacımız işe yarayan parça, satılmış bir parça değil.</p>"
        "<h2>Siparişe başlayın</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişliyi</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">ölçüye özel burç ve rulman '
        "yatağını</a> inceleyebilirsiniz.</p>"
        '<p>Ölçünüz belliyse ya da elinizde örnek parça varsa hemen başlayabiliriz. Sitemizden '
        'kartla online ödeme yapabilir; ölçü ve malzeme danışmanlığı için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _olcuye_ozel_plastik_disli_uretimi():
    return (
        "<h1>Ölçüye Özel Plastik Dişli ve Kramayer Üretimi</h1>"
        '<p class="lead">Kırılan ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz: '
        "düz, helis, konik, sonsuz ve kramayer.</p>"
        "<p>Bir dişli aşındığında ya da kırıldığında iş çoğu zaman durur. Eski makinelerde, "
        "ithal cihazlarda, mutfak robotundan bahçe ekipmanına kadar birçok üründe o dişlinin "
        "yedeği artık üretilmez, piyasada bulunmaz ya da yalnızca komple modül olarak satılır. "
        "Elinizdeki parça küçük bir plastik çark olsa bile onsuz sistem çalışmaz.</p>"
        "<p><strong>Kırık ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz.</strong> "
        "Tek bir parça için bile çalışırız.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Akış basit. Kırık dişliyi ya da net ölçülerini bize iletirsiniz; biz ölçüyü "
        "çıkarır, eşleşecek dişliyle "
        "uyumlu olacak şekilde üretiriz. Modül ve diş adımı biliniyorsa doğrudan kullanır, "
        "bilinmiyorsa numuneden ölçeriz. <strong>Ölçü sizden, üretim bizden.</strong></p>"
        "<h2>Ölçünüze göre ayarladığımız seçenekler</h2>"
        "<p>Standart bir katalog değil, sizin parçanız için üretim yapıyoruz. Belirleyebildiğimiz "
        "başlıklar:</p>"
        "<ul><li><strong>Dişli tipi:</strong> düz (spur), helis, çift helis, konik, sonsuz "
        "(worm), iç dişli, taç dişli ve kramayer.</li>"
        "<li><strong>Ölçüler:</strong> diş sayısı, dış çap, kalınlık ve mil çapı.</li>"
        "<li><strong>Modül / diş adımı:</strong> biliniyorsa değere göre, bilinmiyorsa "
        "numuneden çıkararak.</li><li>Farklı renk seçenekleri.</li></ul>"
        "<p>Bir dişlinin eşleştiği dişliyle çalışabilmesi için aynı modül ve aynı basınç "
        "açısında olması gerekir. Bu yüzden mümkünse eşleşeceği dişliyi ya da net ölçüleri "
        "de isteriz.</p>"
        "<h2>Doğru malzeme: yüke göre seçim</h2>"
        "<p>Bir dişlinin ömrü, ne kadar zorlandığına ve nerede çalıştığına bağlıdır. Sıradan "
        "malzeme (PLA) çabuk yenilir. Isı, nem ve dış koşul varsa PETG, ASA ya da PC; gerçek "
        "yük ve sürtünme varsa karbon veya cam fiber takviyeli malzeme (PA-CF / PA-GF) "
        "öneririz. Bu takviyeli malzemeler sertlik ve aşınma dayanımı bakımından belirgin "
        "biçimde üstündür — yük taşıyan dişlilerde fark buradan gelir.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik dişli, elektrikli el aletlerinden ofis makinelerine, ev ve bahçe "
        "ekipmanından hafif mekanizmalara kadar geniş bir alanda işe yarar. Yüksek torklu ağır "
        "sanayi güç aktarım hatları ya da metalin zorunlu olduğu yerler için doğru cevap "
        "plastik değildir. Parçanızın çalışacağı koşulu bize söyleyin; uyacaksa en dayanıklı "
        "malzemeye yönlendirir, uymuyorsa açıkça belirtiriz. Amacımız çalışan bir parça "
        "teslim etmektir.</p>"
        "<h2>Sipariş ve ölçü danışma</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">ölçüye özel triger kasnağını</a> '
        've <a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman '
        "yatağını</a> inceleyin.</p>"
        '<p>Sitemizden kartla online ödeme yapabilir; dişlinizin fotoğrafı ve ölçüleri için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
    )


def _numuneye_gore_triger_kasnagi_uretimi():
    return (
        "<h1>Numuneye Göre Triger Kasnağı ve Kayışı Üretimi</h1>"
        '<p class="lead">Bulunamayan triger kasnağını profil ve diş sayısına göre, mil tipi '
        "ve flanş seçimiyle üretiyoruz.</p>"
        "<p>Makinenizin, yazıcınızın veya CNC tezgâhınızın triger kasnağı kırılmış ve tam "
        "karşılığını hiçbir yerde bulamıyorsunuz. Model kalkmış, stok tükenmiş, ya da eldeki "
        "kasnak sizin mil çapınıza veya kayış profilinize uymuyor. Piyasadaki hazır kasnaklar "
        "standart ölçülerde gelir; sizin ihtiyacınız ise belirli bir diş sayısı, belirli bir "
        "genişlik ve belirli bir mil bağlantısıdır. Böyle bir parça için tek yol, onu "
        "<strong>ölçüye özel ürettirmektir</strong>.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>İşleyiş basittir. Elinizdeki kırık kasnağı, kayışı ya da ölçülerini bize "
        "iletirsiniz. Kayış profilini, diş sayısını "
        "ve mil detaylarını netleştirir; parçayı verdiğiniz ölçüye göre üretiriz. Numune yoksa "
        "yalnızca ölçülerle de çalışırız. Amaç mevcut kayışınıza ve milinize sorunsuz oturan "
        "bir parça çıkarmaktır.</p>"
        "<h2>Neyi ölçünüze göre ayarlıyoruz?</h2>"
        "<p>Standart bir katalogdan değil, sizin ihtiyacınıza göre üretim yaptığımız için şu "
        "detayların hepsini belirleyebilirsiniz:</p>"
        "<ul><li><strong>Kayış profili:</strong> GT2 (2 / 3 / 5 mm), HTD (3M / 5M / 8M), "
        "T2.5, T5, T10, AT5, MXL, XL, L.</li>"
        "<li><strong>Diş sayısı ve kayış genişliği</strong> — mevcut kayışınıza tam oturacak "
        "şekilde.</li>"
        "<li><strong>Mil bağlantısı:</strong> düz, kanallı (keyway), altıgen ya da D-lama; "
        "ölçtüğünüz <strong>mil çapına</strong> göre.</li>"
        "<li><strong>Yan flanş:</strong> iki tarafta, yalnız üstte, yalnız altta ya da "
        "flanşsız — kayış kaçmasın diye.</li>"
        "<li><strong>Göbek (hub) ve setskur</strong> — mile kilitlemek için, isterseniz.</li>"
        "<li>Farklı renk seçenekleri.</li></ul>"
        "<h2>Doğru malzeme güveni</h2>"
        "<p>Her kasnak aynı koşulda çalışmaz, biz de malzemeyi kullanım yerine göre seçeriz. "
        "Standart iç mekân uygulamaları için dayanıklı temel malzemeler; ısı, UV ve nemli "
        "ortamlarda PETG, ASA veya PC; sürekli yük ve aşınmada karbon ya da cam fiber "
        "takviyeli PA-CF / PA-GF kullanırız. Parçanın nerede döneceğini paylaştığınızda doğru "
        "malzemeye yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Açık olalım: özel ürettiğimiz kasnaklar <strong>düşük–orta yük ve tork</strong> "
        "için uygundur; hafif tahrik, konumlandırma ve düşük güçlü aktarım işlerinde güvenle "
        "çalışır. Yüksek güçlü, ağır sanayi tahrik hatlarında metal kasnağın yerini tutmaz. "
        "Parçanızı çalışacağı yere göre değerlendirir, uygun değilse baştan söyleriz — bu "
        "bizim için güvenin temeli.</p>"
        "<h2>Kasnağınızı ürettirin</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçasını</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişliyi</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç çözümünü</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Bulunamayan triger kasnağınızı ya da kayış kasnağınızı ölçüye özel üretiyoruz. '
        'Ölçülerinizi veya numunenizi paylaşın, üretelim. Sitemizden kartla online ödeme '
        'yapabilir; ölçü ve profil danışmanlığı için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _numuneden_plastik_burc_rulman_uretimi():
    return (
        "<h1>Numuneden Plastik Burç ve Rulman Yatağı Üretimi</h1>"
        '<p class="lead">Aşınan burcu ya da rulman yatağını iç/dış çap ve genişlik '
        "ölçünüze göre üretiyoruz. Standart kod ya da özel ölçüyle çalışıyoruz.</p>"
        "<p>Aşınmış bir burç, yerinde durmayan bir rulman yatağı ya da makinede boşluk yapan "
        "tek bir parça yüzünden koca bir tezgâh durabilir. Çoğu zaman o parça piyasada artık "
        "bulunmaz, üzerinde kod yoktur veya orijinali fahiş fiyatlıdır. Eski parça kırık ya "
        "da yıpranmış olsa bile ondan yola çıkarak yenisini üretiyoruz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Çalışma şeklimiz basit: parçayı ya da ölçüyü getirin, biz ölçüp size özel üretelim. "
        "Elinizde numune varsa iç çap, dış çap ve genişliği bizzat ölçeriz; numune yoksa "
        "vereceğiniz ölçülere göre çalışırız. Sonuç, "
        "montaj yerine oturan ve boşluk yapmayan bir parçadır.</p>"
        "<h2>Plastik burç üretimi: ölçü sizden</h2>"
        "<p>Burç ve rulman yatağını iki yoldan üretiyoruz. Standart bir rulman ölçüsü (608, "
        "6200, 6900, R8 ya da flanşlı F688ZZ gibi) veriyorsanız o koda göre; standart dışıysa "
        "doğrudan iç çap + dış çap + genişlik ölçünüze göre üretiriz. İhtiyaç olan yerlerde "
        "flanşlı seçenek sunarız, böylece parça yatağında eksenel olarak sabit durur. İster "
        "tek parça sabit burç, ister yerinde dönen rulman yatağı olsun, ölçüye özel burç "
        "üretimi ile parçayı uygulamanıza göre çıkarırız. Farklı renk seçenekleri de mümkün.</p>"
        "<p>Numuneden rulman yatağı yaptırma sürecinde en önemli soru şudur: parça nerede, "
        "hangi hızda ve yükte çalışacak? Kullanım "
        "koşulu malzemeyi, malzeme de parçanın ömrünü belirler.</p>"
        "<h2>Doğru malzeme güveni</h2>"
        "<p>Sıradan plastik yerine, işin gereğine göre doğru malzemeyi seçiyoruz. Isıya, "
        "dışarıda çalışacaksa UV ve neme dayanıklı PETG, ASA ya da PC; sürtünme ve "
        "yükün arttığı yerlerde karbon veya cam fiber takviyeli PA-CF / PA-GF gibi yüksek "
        "mukavemetli malzemeler kullanırız. Parça hem ölçünüze hem çalışacağı ortama uygun olur.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik burcun da bir sınırı var, bunu baştan söyleriz: bu parçalar "
        "<strong>düşük–orta hız ve yükte, çoğunlukla kuru (yağsız) çalışma</strong> "
        "için uygundur. Yüksek devirli, ağır yük altındaki ana rulman uygulamalarının yerini "
        "tutmaz. Parçanızın nerede çalışacağını bize anlatın; uygun değilse en baştan "
        "söyleriz, uygunsa doğru malzemeye yönlendiririz. Amaç, size gerçekten işini gören "
        "bir parça vermek.</p>"
        "<h2>Sipariş verin</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçasını</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişliyi</a> ve '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">triger kasnağını</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Ölçünüzü hazırlayın, gerisini biz halledelim. Siteden kartla online ödeme '
        'yapabilir; ölçü danışmanlığı, özel iş veya numune '
        'için WhatsApp hattımıza ulaşabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


# build.py'nin ÜRETTİĞİ yeni sayfalar (hakkimizda/iletisim/sss/gizlilik zaten
# elle yapılmış statik dosya olarak repo'da; onlar üretilmez, korunur).
# slug -> (başlık, meta açıklama, gövde fonksiyonu)
CONTENT_PAGES = [
    ("teslimat-iade", "Teslimat ve İade", "PRUVO teslimat, kargo ve iade/cayma hakkı koşulları.", _teslimat_iade),
    ("mesafeli-satis", "Mesafeli Satış Sözleşmesi", "PRUVO mesafeli satış sözleşmesi.", _mesafeli_satis),
    ("malzeme-rehberi", "Malzeme Rehberi",
     "PLA, PETG, ASA ve TPU malzemelerinin karşılaştırması: ısı, güneş (UV), su ve darbe "
     "dayanımı; hangi parçada hangi malzeme önerilir. Mühendislik malzemeleri (ABS, karbon "
     "katkılı) WhatsApp özel talebiyle.", _malzeme_rehberi),
    ("numuneye-gore-plastik-parca-uretimi", "Numuneye Göre Plastik Parça Üretimi",
     "Kırılan ya da bulunamayan parçanızı getirin; ölçüsünü alıp ölçüye özel, doğru "
     "malzemeyle üretelim. Tek adet olur. Online sipariş ve WhatsApp.", _numuneye_gore_plastik_parca_uretimi),
    ("bulunamayan-yedek-parca-ozel-uretim", "Bulunamayan Yedek Parça Özel Üretim",
     'Servis "parça yok" mu dedi? Üretimi durmuş ya da piyasada olmayan parçayı ölçüsüne '
     "göre özel üretiyoruz. Doğru malzeme, tek adet, online sipariş.", _bulunamayan_yedek_parca_ozel_uretim),
    ("beyaz-esya-plastik-parca-uretimi", "Beyaz Eşya Plastik Parça Üretimi",
     "Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri... Kırılan beyaz eşya "
     "plastiğini ölçüsüne göre üretiyoruz. Numune yeter, tek adet.", _beyaz_esya_plastik_parca_uretimi),
    ("oto-ic-trim-klips-parca-uretimi", "Oto İç Trim ve Klips Parça Üretimi",
     "Torpido ızgara klipsi, kapak kolu, iç trim braketi bulunamıyor mu? Kırılan parçayı "
     "numuneden ölçüye özel üretiyoruz. Dayanıklı malzeme, tek adet.", _oto_ic_trim_klips_parca_uretimi),
    ("makine-parcasi-olcuye-ozel-uretim", "Makine Parçası Ölçüye Özel Üretim",
     "Üretimden kalkmış makinenin plastik dişli, kasnak ya da burcu bulunamıyor mu? Numuneden "
     "ölçüye özel, yük durumuna uygun malzemeyle üretelim.", _makine_parcasi_olcuye_ozel_uretim),
    ("tekne-plastik-parca-ozel-uretim-gocek-fethiye", "Tekne Plastik Parça Üretimi | Göcek-Fethiye",
     "Göcek ve Fethiye'de teknenizin kırılan veya bulunamayan plastik parçasını deniz "
     "koşuluna dayanıklı ASA/PETG ile ölçüye özel üretiyoruz.", _tekne_plastik_parca_ozel_uretim_gocek_fethiye),
    ("kisiye-ozel-logolu-kase-yaptirma", "Kişiye Özel Logolu Kaşe Yaptırma",
     "Yazı, logo ya da ikon işlenmiş kaşenizi ölçünüze göre üretiyoruz: dikdörtgen, kare "
     "veya yuvarlak; düz veya kesikli çerçeve, vidalı ayrı sap. Online sipariş.", _kisiye_ozel_logolu_kase_yaptirma),
    ("olcuye-ozel-conta-uretimi", "Ölçüye Özel Conta ve O-ring Üretimi",
     "Orijinali bulunmayan contayı iç çap ve kesit ölçünüze göre üretiyoruz. Yuvarlak, kare, "
     "pahlı profil; kullanım yerine uygun malzeme. Düşük-orta basınç.", _olcuye_ozel_conta_uretimi),
    ("olcuye-ozel-plastik-disli-uretimi", "Ölçüye Özel Plastik Dişli Üretimi",
     "Kırılan ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz: düz, helis, konik, "
     "sonsuz, kramayer. Yüke göre karbon/cam fiber takviye seçeneği.", _olcuye_ozel_plastik_disli_uretimi),
    ("numuneye-gore-triger-kasnagi-uretimi", "Ölçüye Özel Triger Kasnağı Üretimi",
     "Bulunamayan triger kasnağını profil ve diş sayısına göre üretiyoruz: GT2, HTD, T5/T10, "
     "MXL... Mil tipi ve flanş seçimiyle. Düşük-orta yük için.", _numuneye_gore_triger_kasnagi_uretimi),
    ("numuneden-plastik-burc-rulman-uretimi", "Plastik Burç ve Rulman Yatağı Üretimi",
     "Aşınan burcu ya da rulman yatağını iç/dış çap ve genişlik ölçünüze göre üretiyoruz. "
     "Standart kod ya da özel ölçü. Düşük hız/yük, kuru çalışma.", _numuneden_plastik_burc_rulman_uretimi),
]

# sitemap için TÜM içerik/yasal sayfa slug'ları (statik + üretilen)
SITEMAP_SLUGS = ["hakkimizda", "iletisim", "sss", "gizlilik",
                 "teslimat-iade", "mesafeli-satis", "malzeme-rehberi",
                 "numuneye-gore-plastik-parca-uretimi",
                 "bulunamayan-yedek-parca-ozel-uretim",
                 "beyaz-esya-plastik-parca-uretimi",
                 "oto-ic-trim-klips-parca-uretimi",
                 "makine-parcasi-olcuye-ozel-uretim",
                 "tekne-plastik-parca-ozel-uretim-gocek-fethiye",
                 "kisiye-ozel-logolu-kase-yaptirma",
                 "olcuye-ozel-conta-uretimi",
                 "olcuye-ozel-plastik-disli-uretimi",
                 "numuneye-gore-triger-kasnagi-uretimi",
                 "numuneden-plastik-burc-rulman-uretimi"]
