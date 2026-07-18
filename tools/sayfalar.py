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
        "<p>İlgili çözümler: "
        '<a href="/kirik-plastik-parca-yaptirma/">kırık plastik parçanın yenisini yaptırma</a>, '
        '<a href="/piyasada-bulunmayan-yedek-parca-uretimi/">piyasada bulunmayan yedek parça üretimi</a> ve '
        '<a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a>.</p>'
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
        '<a href="/malzeme-rehberi/">malzeme rehberi</a> sayfalarını inceleyin. '
        '<a href="/olcuye-ozel-izgara-petek-uretimi/">Ölçüye özel ızgara ve menfez</a>, '
        '<a href="/olcuye-ozel-mentese-uretimi/">menteşe</a>, '
        '<a href="/olcuye-ozel-kulp-tutamak-uretimi/">kulp ve tutamak</a> ile '
        '<a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aleti dişli parçaları</a> '
        'için ilgili hizmet sayfalarına geçebilirsiniz.</p>'
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
        'inceleyebilirsiniz. Genel bağlama ve tutturma işleri için '
        '<a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> '
        'sayfasına geçebilirsiniz.</p>'
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
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman yatağını</a> ve '
        '<a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnağı</a> '
        'inceleyin. Tarıma özgü uygulamalar için '
        '<a href="/tarim-makinesi-plastik-parca-uretimi/">tarım makinesi plastik parça üretimi</a> '
        'sayfasına geçebilirsiniz.</p>'
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
        'yatağını</a> inceleyebilirsiniz. Kapatma ve koruma ihtiyacı için '
        '<a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak üretimi</a> '
        'sayfasına geçebilirsiniz.</p>'
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
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç çözümünü</a>, '
        '<a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel konektörü</a>, '
        '<a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketini</a>, '
        '<a href="/olcuye-ozel-profil-beam/">ölçüye özel profili</a> ve '
        '<a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnağı</a> '
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


def _piyasada_bulunmayan_yedek_parca_uretimi():
    return (u"""<h1>Piyasada Bulunmayan Yedek Parçayı Üretiyoruz — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Muadili çıkmayan, hiç ayrı satılmamış ya da modeli çoktan kalkmış parçayı elinizde tutuyorsunuz — biz onu ölçüp yeniden üretiyoruz.</p>
<p>Bazı parçalar için arama motoruna ne yazarsanız yazın sonuç çıkmaz. Çünkü o parça piyasada tek başına hiç satılmamıştır; komple bir grubun içinde gelmiş, tek başına stok kodu bile almamıştır. Ya da üretici o modeli yıllar önce bırakmış, servis desteği tümüyle kapanmıştır. Elinizdeki cihaz, makine ya da mobilya sapasağlam çalışıyor; sırf bu tek plastik parça kırıldığı için kullanılamaz halde bekliyor.</p>
<p>Bu, fiyat karşılaştırıp en ucuzunu bulma meselesi değil. Ortada karşılaştırılacak bir muadil yok. İhtiyacınız olan şey, o parçanın bire bir aynısının yeniden var edilmesi. İşte bizim işimiz tam olarak bu: elinizdeki örnekten yola çıkıp ölçüsüne sadık kalarak parçayı özel üretiyoruz. Numune kırık, eksik ya da deforme olsa bile ölçüleri çıkarıp bütünleyebiliriz; benzer bir işi <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> sayfasında da anlatıyoruz.</p>
<p>Servis desteği hâlâ süren ama yedeği stokta bulunmayan parçalar için ayrı bir sayfamız var — o durumu <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> tarafında ele alıyoruz. Bu sayfa özellikle muadili hiç olmayan, tek başına satılmamış ya da modeli tümden kalkmış parçalar içindir. Kargoyla nereden gönderirseniz gönderin, üretip geri yolluyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık ya da sağlam parçanızın fotoğrafını, varsa eski ölçülerini WhatsApp'tan gönderin; fiziksel numuneyi kargoyla yollayabilirsiniz.</li>
<li><strong>Ölç.</strong> Parçayı milimetrik ölçeriz; kırık veya aşınmışsa özgün halini tersine çıkarır, montaj noktalarını ve tork/temas yüzeylerini doğrularız.</li>
<li><strong>Üret.</strong> Onayınızın ardından doğru malzemeyle özel üretir, kargoyla adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her parça kendine özgü olduğu için üretimi tek tek sizin örneğinize göre kurarız:</p>
<ul>
<li><strong>Bire bir ölçü</strong> — dış boyut, delik çapları, delikler arası mesafe, vida/cıvata yuvaları elinizdeki örneğe göre.</li>
<li><strong>Montaj detayı</strong> — geçme, vidalı, klipsli ya da kanal-ray bağlantı; tırnak ve kilit noktaları özgün parçadaki gibi.</li>
<li><strong>Malzeme sınıfı</strong> — kullanılacağı ortama göre standart, ısı/UV/nem dayanımlı ya da yüksek mukavemetli seçim.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür parçalarda mevcut ürününüze yakın ton.</li>
<li><strong>Eksik/kırık numune tamamlama</strong> — parça bütün değilse ölçüyü çıkarıp özgün formu bütünleriz.</li>
</ul>
<p>Kendi çiziminiz ya da teknik resminiz varsa onunla da çalışırız; <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfası bu yönü daha ayrıntılı anlatır.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç mekanda, yük altında olmayan parçalarda standart malzeme yeterlidir. Güneş, ısı, nem ya da dış ortam söz konusuysa PETG, ASA veya PC gibi dayanıklı malzemelere çıkarız. Zorlanan, tork veya darbe gören parçalarda karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangi parçanın nereye oturduğunu <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında açıklıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parça plastik esaslıdır; doğru malzemeyle çok yerde orijinalin işini görür ama sınırını açıkça söyleriz. Yük taşıyan, sürekli yüksek tork ya da ağır darbe altında çalışan metal bir parçanın tam yerine geçmesini vaat etmeyiz. Bağlantı, kapak, klips, dişli/kasnak gibi düşük–orta yük ve tork gören parçalarda ise doğru malzemeyle uzun ömürlü sonuç alırsınız. Parçanızın nerede çalıştığını sorar, buna göre yönlendiririz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Parçanızın fotoğrafını ve ölçülerini WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; birlikte netleştirip üretime alalım. Ölçüsü ve malzemesi netleşen işlerde siteden kartla online ödemeyle de sipariş verebilirsiniz. Numuneyi kargoyla gönderin, üretip adresinize yollayalım.</p>""")


def _kirik_plastik_parca_yaptirma():
    return (u"""<h1>Kırık Plastik Parça mı? Yenisini Üretelim — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizde kırılmış, çatlamış ya da parçalanmış bir plastik parça var ve piyasada aynısını bulamıyorsunuz; biz o kırık numuneden yenisini ölçüye özel üretiyoruz.</p>
<p>Çoğu kırık parça öyle görünür: küçük bir kulakçık kopmuştur, bir tırnak kırılmıştır, gövde ikiye ayrılmıştır. Onarmaya çalışırsınız, yapıştırırsınız, bir süre sonra aynı yerden yine gider. Aslında aradığınız şey tamir değil — o parçanın <strong>sağlam bir yenisi</strong>. Ama üretici çoktan modeli kaldırmıştır, yedek parça listesinde yoktur ya da "komple takım al" derler. Sizin tek ihtiyacınız o küçük plastik parça.</p>
<p>İşte tam burada devreye giriyoruz. Kırık parça çöp değil, ölçünün ta kendisidir. Elinizdeki kırık örnek çoğu zaman yeniyi çıkarmaya yeter: kırık kenarları birleştirir, ölçüleri alır, deforme olmuş yerleri toparlar ve parçayı sıfırdan, ölçüye özel yeniden üretiriz. Parçaların çoğu ikiye ayrılmış olsa bile iki yarım bir araya gelince tam geometri okunur. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Kayıp bir tırnak, aşınmış bir diş, kopmuş bir bağlantı — bunların hepsi telafi edilebilir. Amaç, orijinaline bakan ama gerektiğinde daha dayanıklı malzemeden çıkan bir parça vermek. Kırık parçadan yenisini yaptırma işi, aslında bir kez doğru yapıldığında bir daha kırılmayan parçayı almaktır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir / gönder.</strong> Kırık parçayı kargoyla bize yollayın; parçalıysa tüm kırık kısımları birlikte koyun — eksik kenar, ölçü kaybı demek.</li>
<li><strong>Ölç.</strong> Kırık örnekten ölçüleri çıkarır, deforme veya aşınmış bölgeleri toparlar, montaj noktalarını doğrularız. Emin olamadığımız bir nokta olursa size sorarız.</li>
<li><strong>Üret.</strong> Onayınızdan sonra parçayı ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Ebat ve geometri:</strong> kırık numunenin birebir ölçüsünde ya da istediğiniz noktada düzeltilmiş ölçüde.</li>
<li><strong>Kopan/aşınan detay:</strong> kırılan tırnak, kulakçık, diş veya bağlantı noktası yeniden oluşturulur.</li>
<li><strong>Bağlantı biçimi:</strong> vida deliği, geçmeli tırnak, klips yuvası aslına uygun konumlandırılır.</li>
<li><strong>Dayanım kademesi:</strong> aynı yerden bir daha kırılmaması için parçayı daha güçlü malzemeye taşıyabiliriz.</li>
<li><strong>Farklı renk seçenekleri:</strong> görünür parçalarda size uygun renk.</li>
</ul>
<p>Benzer işler için <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> ve <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> sayfalarına da bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Parçanın çalışacağı yere göre malzemeyi seçeriz. İç mekânda, düşük yük altında çalışan standart parçalar için dayanıklı bir taban malzeme yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalan parçalarda PETG, ASA veya PC gibi dayanıklı malzemelere çıkarız. Yük taşıyan, tork gören, sık zorlanan parçalarda ise karbon ya da cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Beyaz eşya parçaları için ayrıntı: <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a>. Malzeme seçiminin tümü: <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Dürüst sınır</h2>
<p>Kırık parçanın yenisini üretebilmemiz için elimizde okunabilir bir geometri olması gerekir; parça toz haline gelmişse ya da kritik bir bölge tamamen kayıpsa ölçü çıkmaz. Ürettiğimiz parça, malzemenin sınırları içinde çalışır: yük taşıyan bağlantılarda montaj/hafif yük, dişli-kasnak türü parçalarda düşük–orta tork esas alınır. Parçayı çalışacağı koşula göre doğru malzemeye yönlendirir, yapamayacağımız zorlamayı baştan söyleriz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödeyerek siparişinizi başlatabilir, kırık parçanızı kargoyla gönderebilirsiniz. Ölçü danışmanlığı, özel iş ve emin olamadığınız durumlar için WhatsApp: <strong>+90 545 138 6526</strong>. Kırık parçayı elinizde tutun — o, yenisinin ölçüsüdür.</p>""")


def _tek_adet_ozel_parca_uretimi():
    return (u"""<h1>Tek Adet Özel Parça Üretimi — Minimum Sipariş Yok</h1>
<p class="lead">Kırılan, kaybolan ya da hiçbir yerde bulamadığınız o tek parçayı, kalıp masrafı olmadan ve adet zorunluluğu olmadan ölçüsüne birebir üretiriz.</p>
<p>Elinizde tek bir parça var. Kırıldı, aşındı ya da orijinali yıllar önce üretimden kalktı. Bir tedarikçiye sorduğunuzda ilk duyduğunuz cümle hep aynı: "Kalıp çıkarmamız gerekir, o da şu kadar tutar" ya da "en az 500 adet basarız, altına inmeyiz." Tek bir parça için kalıp masrafını göze almak mantıksız; 500 adet almaksa saçma. Arada sıkışıp kalıyorsunuz.</p>
<p>Biz tam bu boşluk için varız. Bizde <strong>minimum sipariş yok</strong> — bir tanesi de üretilir, ikisi de. Kalıp çıkarmadığımız için o maliyet faturanıza binmez; tek parçanın kendi maliyetini ödersiniz, o kadar. İster elinizdeki numuneyi ölçelim, ister bir teknik çizim gönderin, ister tek seferlik bir prototip fikri olsun — adetli olmayan özel üretim bizim standart işimiz.</p>
<p>Bu, prototip aşamasındaki bir tasarımı tek parça yaptırmak isteyen mühendisten, evindeki bir cihazın tek bir dişli-tırnağını arayan tamirciye kadar herkes için geçerli. "Sadece bir tane lazım, kimse yapmıyor" dediğiniz noktada devreye giriyoruz. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki kırık ya da eski parçayı kargoyla bize gönderin; ya da ölçülerini, fotoğrafını, varsa çizimini iletin. Numune yoksa nereye takıldığını anlatın, birlikte netleştiririz.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçeriz; oturması gereken deliği, dişi, kenar boşluğunu birebir çıkarırız. Tek adette hata payı olmasın diye kritik ölçüleri sizinle teyit ederiz.</li>
<li><strong>Üret</strong> — Onayladığınız ölçüde tek parçanızı üretir, kargoyla adresinize yollarız. İşin doğasına göre en uygun malzemeyi öneririz.</li>
</ol>
<h2>Doğru malzeme</h2>
<p>Her parça aynı malzemeyi kaldırmaz; seçimi işin çalışacağı yere göre yaparız. İç mekân, düşük yük ve görünürde duracak parçalarda standart malzeme yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalacak bir parça için <strong>PETG, ASA veya PC</strong> gibi dayanıklı malzemelere çıkarız. Gerçek mukavemet, tork ya da darbe gereken yerlerde ise <strong>karbon ya da cam fiber takviyeli (PA-CF / PA-GF)</strong> seçeneği devreye girer. <strong>Farklı renk seçenekleri</strong> de mümkün. Hangi parçanın hangi malzemeyi hak ettiğini siz bilmek zorunda değilsiniz — kullanım yerini söyleyin, doğru malzemeye biz yönlendirelim.</p>
<h2>Dürüst sınır</h2>
<p>Üretilen parça, malzemesinin sınırları içinde iş görür; bunu baştan söylemek işimizin bir parçası. Bağlantı, braket, kapak, tutucu gibi <strong>yük taşımayan montaj parçalarında</strong> ve prototiplerde sonuç çok sağlıklı olur. Aşırı yük altında sürekli çalışacak, yüksek sıcaklıkta zorlanacak ya da metalin yerini birebir tutması beklenen kritik güvenlik parçalarında ise sınırı açıkça belirtir, gerekiyorsa sizi doğru malzemeye ya da farklı bir çözüme yönlendiririz. Tek adet iş de olsa yapmayacağımızı yapabiliriz demeyiz.</p>
<p>Benzer ihtiyaçlarda şu sayfalara da bakabilirsiniz: <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> ve <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parçanın özel üretimi</a>.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ya da numunenizi hazırlayın, gerisini biz halledelim. Ürünleri inceleyip <strong>kartla online ödemeyle</strong> doğrudan sipariş vermek için <a href="/">mağazamıza</a> göz atabilirsiniz. Tek parçalık özel işiniz, ölçü danışması ya da elinizdeki numuneyle ilgili sorularınız için WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_baglanti_konektor():
    return (u"""<h1>Ölçüye Özel Bağlantı ve Konektör Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Kırılan bağlantı parçasının yerine takılanı bulamıyorsanız, o parçayı ölçünüze göre üretiyoruz.</p>
<p>Boruyu boruya, çubuğu çubuğa birleştiren o küçük ekleme parçası kırıldığında iş çoğu zaman durur. Piyasada tam o çapta, tam o açıda konektör yoktur; yakın olanı zorla takarsınız, ya oynar ya çatlar. Eski parça artık üretilmiyordur, marka bilinmiyordur, ölçüsü standart değildir. "Benzeri olur mu?" diye dükkan dükkan gezmek yerine tek bir çözüm var: elinizdeki parçayı ya da birleştirmek istediğiniz boruların ölçüsünü bize verin.</p>
<p>Biz ölçüye özel bağlantı ve konektör üretimi yapıyoruz. Kaç kollu olacağını, hangi çapta boruyu geçireceğini, kolların hangi açıyla duracağını siz söylüyorsunuz; parçayı o ölçülere göre üretip gönderiyoruz. Sergi, stant, çadır iskeleti, sera, raf sistemi, korkuluk, hobi konstrüksiyon — çubuk birleştirme ekleminin standart dışı olduğu her yerde iş görür. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Örnek parça, fotoğraf ya da iki borunun dış çapı ve aradaki açı — elimize ne geçerse ona göre üretime başlarız. Daha büyük mekanik işleriniz için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık konektörü, birleştireceğiniz boruları ya da net bir fotoğraf/ölçü krokisini WhatsApp'tan gönderin.</li>
<li><strong>Ölç:</strong> Boru/çubuk çapını, kol sayısını, açıyı ve geçme sıkılığını birlikte netleştiririz.</li>
<li><strong>Üret:</strong> Onayınızdan sonra parçayı ölçüye özel üretip kargoyla adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Boru bağlantı konektörü yaptırırken şu değerleri sizin işinize göre belirliyoruz:</p>
<ul>
<li><strong>Kol sayısı:</strong> 2 kol (düz ek veya dirsek), 3 kol (T / Y / köşe birleşimi), 4 kol (X kesişim).</li>
<li><strong>Kol kesiti:</strong> yuvarlak, kare veya sekizgen — geçireceğiniz profile göre.</li>
<li><strong>Geçecek çubuk/boru çapı:</strong> milimetrik olarak sizin borunuza göre.</li>
<li><strong>Geçme sıkılığı:</strong> sıkı (sabit oturur), normal ya da gevşek (sökülüp takılabilir).</li>
<li><strong>Kol boyu:</strong> her kolun uzunluğu ayrı ayrı ayarlanır.</li>
<li><strong>Kollar arası açı:</strong> düz, dirsek ya da istediğiniz özel derece.</li>
<li><strong>Farklı renk seçenekleri.</strong></li>
</ul>
<h2>Doğru malzeme</h2>
<p>Konektörü nerede kullanacağınıza göre malzemeyi seçeriz. İç mekanda, hafif yükte standart dayanıklı malzeme yeter. Dışarıda, güneş ve nem altında, teknede kullanılacaksa ısıya ve UV'ye dayanıklı PETG, ASA veya PC'ye çıkarız. Titreşimli, zorlayan, taşıyıcı bir noktadaki birleşim içinse karbon veya cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangi malzemenin gerektiğini birlikte kararlaştırırız; <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında sınıfların farkını ayrıntılı bulabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Bağlantı ve konektör parçaları yük dışı montaj ve birleştirme işleri içindir — iskeleti bir arada tutar, hizalar, sabitler. Üzerine sürekli ağır darbe binen, insan taşıyan ya da yapısal güvenlik gerektiren taşıyıcı bir noktada tek başına ana yük elemanı olarak önermeyiz. Parçanın çalışacağı yeri baştan konuşur, gereken yerde daha güçlü malzemeye yönlendirir, taşıyamayacağı yükü de açıkça söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçüsü belli konektörleri siteden kartla online ödeyerek sipariş edebilirsiniz. Ölçü danışmak, örnek parça göndermek veya özel açı/çap istemek için WhatsApp'tan yazın: <strong>+90 545 138 6526</strong>. Örnekten birebir üretime dair <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre üretim</a> yaklaşımımız burada da aynı: getirin, ölçelim, üretelim.</p>""")


def _olcuye_ozel_montaj_braketi():
    return (u"""<h1>Ölçüye Özel Montaj Braketi Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki parça standart ölçüde değilse, hazır braket asla tam oturmaz; ölçüye özel montaj braketi üretimi ile deliğinden açısına kadar tam sizin yerinize göre üretiriz.</p>
<p>Piyasadaki köşebent ve L braketler belli deliklere, belli kalınlıklara göre seri üretilir. Sizin montajınız ise çoğu zaman araya sıkışmış bir boşluğa, tuhaf bir açıya ya da mevcut deliklerle hizalanması gereken özel bir vida düzenine oturur. Standart braketi zorla eğip bükmek, fazladan delik açmak veya iki parçayı üst üste bindirmek hem çirkin durur hem güveni bozar.</p>
<p>Bir makinede, panoda, tekne içinde ya da mobilyada "tam buraya oturan bir parça olsa" dediğiniz noktayı biz üretiriz. Kırılan orijinal braketi getirin, fotoğrafını veya ölçüsünü paylaşın; aynısını ya da geliştirilmiş halini çıkaralım. Özel köşebent braket yaptırma, açılı montaj braketi üretimi ya da mevcut delik aralığına birebir oturan L braket ölçüye özel üretim — hepsi aynı akışla ilerler. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Bağlantı noktalarını taşıyan makine gövdeleri için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık braketi, montaj boşluğunun ölçüsünü veya basit bir el çizimini iletin. Kargoyla parçayı da gönderebilirsiniz; üretip yollarız.</li>
<li><strong>Ölç</strong> — Kalınlık, kol uzunlukları, iç açı ve vida deliklerinin yerini birlikte netleştiririz; nereye monte edileceğine göre en doğru geometriyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra ölçüye özel üretiriz ve adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Braket tipi:</strong> açılı/köşebent, köşe, düz plaka, T, L veya Y formu</li>
<li><strong>İç açı:</strong> açılı braketlerde istediğiniz dereceye göre (90°, 120° veya ara açılar)</li>
<li><strong>Ölçüler:</strong> kalınlık × genişlik × kol uzunluğu milimetrik olarak size özel</li>
<li><strong>Vida düzeni:</strong> M3–M8 veya inç ölçü; her kola delik sayısı ve delik aralığı sizin montajınıza göre</li>
<li><strong>Takviye:</strong> açılı braketlerde payanda/flanş desteği ile ek sağlamlık</li>
<li><strong>Simetri:</strong> sağ/sol ayna çift olarak, karşılıklı montaj için</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<h2>Doğru malzeme</h2>
<p>İşin yerine göre malzemeyi birlikte seçeriz. İç mekân, düşük yüklü montajlar için standart dayanımlı malzeme yeterlidir. Isı, UV, nem ya da deniz koşulu varsa PETG, ASA veya PC gibi dayanıklı malzemelere çıkarız. Yükü gerçekten taşıyan, titreşim ve zorlanma altındaki braketlerde ise karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. <a href="/malzeme-rehberi/">Malzeme rehberi</a> sayfasında hangi koşula hangi malzemenin uyduğunu ayrıntılı anlatıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Braket, yük-dışı ve montaj amaçlı bir bağlantı parçasıdır; iki yüzeyi hizalar, konumlar, hafif kuvvetleri taşır. Ana taşıyıcı kiriş, kaldırma noktası ya da sürekli ağır darbe/çekme alan kritik yapı elemanı olarak konumlandırmayız. Nereye monte edeceğinizi söyleyin, o yüke göre malzeme ve takviyeyi doğru seçelim — taşıyabileceğinden fazlasını vaat etmeyiz.</p>
<p>Numuneden birebir kopya çıkarma yaklaşımımızı <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a> örneğinde de görebilirsiniz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödemeyle sipariş verebilirsiniz. Ölçü danışmanlığı, özel geometri ya da numune göndermek için WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Braketinizi getirin, ölçelim, üretelim.</p>""")


def _olcuye_ozel_profil_beam():
    return (u"""<h1>Ölçüye Özel Profil, Kızak ve Kiriş Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki profil, kızak ya da kiriş piyasada tam ölçüsüyle yok mu; kırıldı, eğildi, standart boy tutmuyor mu? Ölçüsünü siz verin, biz ölçüye özel üretip kargoyla yollayalım.</p>
<p>Standart bir sigma profil, U kanal ya da köşebent bulmak kolay — ama işiniz milimetrik oturmadığında o standart boy hiçbir işe yaramıyor. Bir dolabın içine tam giren kızak, bir tezgâhın altına oturan hafif kiriş, özel bir kesitte bir bağlantı profili... Bunlar rafta satılmaz. Mağazadan mağazaya dolaşıp "yaklaşık" bir şey almak yerine, gerçek ölçünüzü söyleyin.</p>
<p><strong>Ölçüye özel profil üretimi</strong> işimizin çekirdeğinde bu var: kesit tipini, yüksekliğini, genişliğini, et kalınlığını ve boyunu siz belirlersiniz; biz o ölçüde üretiriz. İster mevcut bir parçayı örnek gönderin, ister ölçüleri yazın — sonucu size özel çıkarırız. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Aynı mantıkla ürettiğimiz diğer ölçüye özel işler için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> ve <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a> sayfalarına da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir/gönder</strong> — kırık ya da örnek profili kargoyla yollayın, ya da kesit tipini ve ölçüleri (yükseklik × genişlik × et kalınlığı × uzunluk) bize iletin.</li>
<li><strong>Ölçelim</strong> — kesiti ve ölçüleri netleştirir, kullanım yerinize göre doğru malzemeyi öneririz.</li>
<li><strong>Üretelim</strong> — ölçüye özel üretip adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kesit tipi:</strong> I, T, L köşebent, Z, U kanal, kutu/dikdörtgen, çokgen, elips ve alüminyum sigma profil formu.</li>
<li><strong>Alüminyum sigma standart boyu:</strong> 2020, 3030, 4040, 4545, 5050, 6060, 8080, 100 serisine uygun kesit.</li>
<li><strong>Ana ölçüler:</strong> yükseklik × genişlik × et kalınlığı × uzunluk — hepsi milimetrik, size göre.</li>
<li><strong>İçi dolu ya da boru/boşluklu</strong> gövde — ağırlık ve kullanıma göre.</li>
<li><strong>Çokgen kesitte kenar sayısı:</strong> 5–18 arası.</li>
<li><strong>Farklı renk seçenekleri</strong> — kullanım yerine uygun tonlar.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekân ve hafif kullanım için dayanıklı temel malzeme yeterli. Isıya, UV'ye, neme ya da deniz koşuluna maruz kalacak profillerde PETG, ASA veya PC'ye çıkarız. Yük altında biçimini koruması gereken, daha sert ve mukavemetli kiriş/kızak gerekiyorsa karbon ya da cam fiber takviyeli PA-CF / PA-GF öneririz. Parçanın nerede çalışacağını söyleyin, malzemeyi ona göre seçelim. Malzeme seçenekleri ve hangi koşulda hangisinin doğru olduğu için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: ürettiğimiz profil, kızak ve kirişler <strong>yük taşıyan yapısal eleman değildir</strong> — hafif, yük-dışı kullanım içindir. Kılavuz kızağı, kablo/hat taşıyıcısı, hafif çerçeve, montaj profili, konumlandırma kirişi gibi işlerde çok iyi sonuç verir. Ana taşıyıcı gövde, üzerine yük binen ya da darbe alan konstrüksiyon içinse metal profil doğru tercihtir; sizi yanıltmayız. En uygun malzemeyle, sınırını bilerek üretiriz.</p>
<h2>Sipariş</h2>
<p>Siteden kartla online ödemeyle ölçüye özel siparişinizi verebilirsiniz. Kesit, ölçü ya da malzeme konusunda emin değilseniz WhatsApp'tan yazın, birlikte netleştirelim: <strong>+90 545 138 6526</strong>. Ölçünüzü gönderin, üretip yollayalım.</p>""")


def _kasnak_olcuye_ozel_uretim():
    return (u"""<h1>Ölçüye Özel Kasnak Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki kasnak kırıldı ya da aşındı, tam karşılığını hiçbir yerde bulamıyorsanız; ölçüsünü verin, birebir karşılığını üretelim.</p>
<p>Eski makinede, çırpıcıda, konveyörde, pompada ya da hobi tezgahında dönen bir kayış kasnağı çatladığında iş çoğu zaman durur. Piyasada aynı çapta, aynı oluk sayısında, aynı mil çapında hazır parça bulmak neredeyse imkansızdır; "yakın" olan da kayışı oturtmaz, titreşim yapar, kısa sürede yeniden atar. Marka gitmiş, model plakası silinmiş, üretici parçayı bırakmışsa iş iyice çıkmaza girer.</p>
<p>PRUVO tam da bu noktada devreye girer. Ölçüye özel kasnak üretimi bizim işimiz: elinizdeki numuneden ya da verdiğiniz ölçülerden yola çıkıp, kayışınıza doğru oturan kasnağı üretiriz. V kayış kasnağı yaptırma mı, düz kayış kasnağı üretimi mi, yoksa kordon (yuvarlak kayış) kasnağı mı fark etmez — mevcut sisteminize göre çözeriz.</p>
<p>Kayışın yaptırdığınız numuneden kasnak üretimi en garantili yoldur: kırık parçayı kargoyla gönderin, ölçüp aynısını çıkaralım. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık ya da örnek kasnağı kargoyla bize gönderin; parça yoksa çap, oluk sayısı, mil çapı ve kayış tipini iletin.</li>
<li><strong>Ölç:</strong> Kanal profilini, dış çapı ve göbek bağlantısını milimetrik ölçer, kayışınıza göre teyit ederiz.</li>
<li><strong>Üret:</strong> Onaydan sonra üretip adresinize yollarız; çalışacağı yere göre doğru malzemeye yönlendiririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kayış tipi:</strong> V-kayış, düz kayış ya da kordon (yuvarlak kayış) — hangisiyle çalışıyorsanız ona göre.</li>
<li><strong>Kanal (oluk) sayısı:</strong> Tek oluktan çok oluklu kasnağa kadar mevcut kayış düzeninize göre.</li>
<li><strong>Dış çap (mm):</strong> Devir/oran ihtiyacınıza uygun tam ölçü.</li>
<li><strong>Mil çapı ve göbek bağlantısı:</strong> Düz geçme, kanallı (kama yuvalı) ya da setskur (sıkma vidalı) göbek.</li>
<li><strong>Yan flanş:</strong> Kayışın kasnaktan kaçmaması için yanak/flanş ekleriz.</li>
<li><strong>Farklı renk seçenekleri:</strong> İhtiyacınıza göre renk çözeriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Kapalı ortamda, ılıman koşulda çalışan bir kasnak için standart mühendislik plastiği yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalan yerlerde PETG, ASA veya PC tercih ederiz. Yükün ve torkun arttığı, aşınmanın hızlandığı uygulamalarda ise karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemetli üretim yaparız. Parçanın nerede döneceğini bize söyleyin; malzemeyi ona göre seçelim.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz kasnak <strong>düşük–orta yük ve tork</strong> aralığı içindir: hobi tezgahı, hafif konveyör, küçük pompa, çırpıcı, model/prototip düzenekleri gibi işler. Ağır sanayi tahriki, yüksek devirli güç aktarımı ya da yüksek tork taşıyan ana kayış-kasnak hattı için tek başına önermeyiz. Zaman/senkron gerektiren dişli kayış (GT2/HTD triger) işiniz varsa doğru sayfa <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a>; dişli çark ihtiyacınız için <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli üretimi</a>, mil yatağı için <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden plastik burç/rulman üretimi</a> sayfalarına bakın. Genel bir makine parçası mı arıyorsunuz? <a href="/makine-parcasi-olcuye-ozel-uretim/">Makine parçası ölçüye özel üretim</a> sayfası başlangıç noktanız olsun.</p>
<h2>Sipariş</h2>
<p>Siparişi siteden kartla online verebilirsiniz. Ölçü paylaşmak, numunenizi konuşmak ya da uygunluk sormak isterseniz WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Kırık kasnağı gönderin, doğru karşılığını üretip yollayalım.</p>""")


def _olcuye_ozel_vida_somun_civata_uretimi():
    return (u"""<h1>Ölçüye Özel Vida, Somun ve Cıvata Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Piyasada bulunamayan çapta, adımda ya da malzemede bir bağlantı elemanına mı ihtiyacınız var? Ölçünüzü verin, size özel vida, somun ve cıvatayı üretip gönderelim.</p>
<p>Standart cıvata her yerde; asıl sorun standart olmayanı bulmakta başlar. Kırılan bir plastik somunun tam karşılığı yok, eski bir makinenin diş adımı bugünkü kataloglara uymuyor, ya da metal bir bağlantının iletken olması işinizi bozuyor. Bu noktada mağazadan mağazaya dolaşmak yerine parçanın kendisini çözüme dönüştürüyoruz.</p>
<p>Elinizdeki numuneyi ya da ölçüleri esas alıyoruz. Özel çap, özel diş adımı, standart dışı kafa biçimi — hangi detay sizi zorluyorsa onu ölçüye özel üretiyoruz. Trapez ve ACME hareket vidalarında olduğu gibi piyasada hazır karşılığı zor bulunan formları, ayar ve konumlandırma mekanizmalarınız için milimetrik çıkarıyoruz.</p>
<p>Metal olmayan, yalıtımlı bağlantı arayanlar için de doğru yerdesiniz. Elektronik montajda kısa devre riskini kaldıran, ısı köprüsü oluşturmayan, korozyona girmeyen plastik somun ve cıvataları ölçünüze göre hazırlıyoruz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçanızı, teknik çizimi ya da yalnızca ölçülerinizi bize iletin. Numune yoksa çap, boy ve diş adımını yazmanız yeterli.</li>
<li><strong>Ölç</strong> — Diş tipini, kafa biçimini ve kullanım yerini birlikte netleştirir, işe uygun malzemeye yönlendiririz.</li>
<li><strong>Üret</strong> — Onaydan sonra size özel üretir, kargoyla adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Ürün tipi:</strong> başlı cıvata / dişli mil-saplama / somun / pul</li>
<li><strong>Ölçü standardı:</strong> metrik (M) / inç (UTS) / tümüyle özel çap + adım</li>
<li><strong>Ölçü ve boy:</strong> M2–M20 arası çap, milimetre hassasiyetinde boy</li>
<li><strong>Diş tipi:</strong> kaba, ince, trapez, ACME veya kare (hareket vidası için)</li>
<li><strong>Kafa tipi:</strong> gömme, yuvarlak, imbus, altıgen ya da pan</li>
<li><strong>Tornavida ağzı:</strong> imbus, torx, yıldız veya düz</li>
<li><strong>Somun ve pul:</strong> somun şekli ve kalınlığı, normal ya da geniş pul boyu</li>
<li><strong>Farklı renk seçenekleri</strong> — montajınıza uygun renkte</li>
</ul>
<p>Belirsiz vaat yerine gerçek ayarları konuşuyoruz; hangi kombinasyon işinizi görüyorsa onu üretiyoruz. Daha karmaşık montajlar için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Kullanım yeri malzemeyi belirler. İç mekan, hafif ayar ve hobi işleri için standart dayanımlı seçenek yeterlidir. Isı, UV, nem ya da deniz koşuluna açık bağlantılarda PETG, ASA veya PC gibi dayanıklı malzemelere çıkarız. Yük ve tork taşıyan, tekrar tekrar sökülüp takılan yerlerde ise karbon ya da cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Malzeme seçiminde tereddüt ederseniz <a href="/malzeme-rehberi/">malzeme rehberi</a> yol gösterir.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: ölçüye özel ürettiğimiz vida ve somunlar hafif–orta yük, ayar, yalıtım ve hobi işleri içindir. Yüksek tork altında sürekli çalışan, güvenlik kritik ya da ağır makine bağlantılarında çelik cıvatanın yerine geçmez. İşiniz yapıya girer girmez size bunu söyler, doğru malzemeye ya da metal çözüme yönlendiririz. Sızdırmazlık gerektiren noktalarda <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> ile tamamlayabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Siparişinizi siteden kartla online ödemeyle verebilirsiniz; ölçüye özel işler dahil güvenli ödeme açık. <a href="/">Ürünleri incelemek</a> ve sipariş için mağazamıza göz atın. Ölçü danışmanlığı, özel iş ve numune paylaşımı için WhatsApp hattımız da hazır: <strong>+90 545 138 6526</strong>. Ölçünüzü iletin, gerisini biz halledelim.</p>""")


def _olcuye_ozel_yay_uretimi():
    return (u"""<h1>Ölçüye Özel Plastik Yay Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Kırılan ya da piyasada tam boyu bulunamayan bir bası yayını, elinizdeki ölçüye göre üretip yolluyoruz.</p>
<p>Bir kapak mekanizması takılıyor, bir klips artık geri itmiyor, tampon içindeki küçük yay kırılmış ve o parçanın kodu, markası, yedeği hiçbir yerde yok. Standart bir yay katalogundan geçen ürün sizinkine ne boyca ne kuvvetçe uyuyor; ya çok sert, ya çok uzun, ya oturmuyor. Bu, çelik bir yay değil ama çelik yay da gerektirmiyor — sadece belirli bir boyda, belirli bir yumuşaklıkta geri dönüş kuvveti isteyen bir eleman.</p>
<p>İşte bu noktada devreye giriyoruz. Kırık parçanızı, eski yayın ölçülerini ya da yerine oturması gereken boşluğun ölçüsünü bize iletin; biz o yayı milimetrik olarak, ihtiyacınız olan sertlikte özel üretelim. Elinizde numune yoksa boy, çap ve ne kadar kuvvet beklediğinizi konuşarak da çıkarabiliriz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>İki farklı yay ailesi üretiyoruz: klasik <strong>spiral bası yayı</strong> (sıkışıp geri açılan, oturaklı yay) ve <strong>dalga / serpantin flexure elemanları</strong> (şerit formunda, esneyerek geri dönen yaylar). Hangisinin işinize uyduğunu ölçünüze bakıp söyleriz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık yayı, numuneyi ya da yerine gireceği boşluğun ölçüsünü kargoyla gönderin veya WhatsApp'tan fotoğraf ve ölçüleri iletin.</li>
<li><strong>Ölç</strong> — Serbest boy, çap, sarım ve beklenen kuvveti çıkarır, doğru yay tipini ve malzemeyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Yay tipi:</strong> spiral bası yayı ya da dalga / serpantin (flexure) form</li>
<li><strong>Spiral için:</strong> serbest boy, dış çap, aktif sarım sayısı, tel çapı ve düz oturma ucu</li>
<li><strong>Dalga için:</strong> form seçimi (sinüs, kare, üçgen, testere ya da darbe profili), genlik, çevrim sayısı, toplam boy ve şerit kalınlığı</li>
<li><strong>Sertlik / yumuşaklık:</strong> tel çapı ve sarım sayısına göre daha sert ya da daha yumuşak geri dönüş</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<p>Bu maddeleri sizin uygulamanıza göre birlikte netleştiriyoruz; ölçü kağıt üzerinde değil, gerçek parçanız üzerinden çıkıyor.</p>
<h2>Doğru malzeme</h2>
<p>Yayın çalışacağı yer malzemeyi belirler. İç mekanda, ılıman koşulda çalışan bir geri dönüş yayı için standart malzeme yeterli. Isı, nem, UV ya da açık hava söz konusuysa PETG, ASA veya PC gibi dayanıklı malzemelere çıkıyoruz. Tekrarlı yükleme altında daha yüksek mukavemet ve yorulma direnci gereken yerlerde ise karbon ya da cam fiber takviyeli PA-CF / PA-GF öneriyoruz. Aynı mantığı diğer parçalarınızda da uyguluyoruz; ayrıntı için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz yaylar hafif kuvvet ve geri dönüş işleri içindir: klips, kapak yayı, tampon, hafif basıya karşı geri iten elemanlar. Yüksek kuvvetli, sürekli ağır yük taşıyan ya da yorulma kritik bir çelik yayın yerine geçmez. Beklediğiniz kuvveti bize söyleyin; iş bu sınırın dışına çıkıyorsa açıkça belirtir, boşuna üretim yapmayız.</p>
<h2>Sipariş</h2>
<p>Site üzerinden kartla online ödeyip sipariş verebilir ya da ölçünüzü konuşmak için WhatsApp'tan <strong>+90 545 138 6526</strong> hattına yazabilirsiniz. Yayla birlikte çalışan bir tespit ya da montaj parçası da mı lazım — <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> ve <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfalarımıza göz atın. Kırık parçayı gönderin, ölçelim, üretip yollayalım.</p>""")


def _elektronik_cihaz_plastik_parca_uretimi():
    return (u"""<h1>Elektronik Cihazın Kırık Plastik Parçasını Üretelim</h1>
<p class="lead">Cihaz sağlam çalışıyor ama küçücük bir plastik kırıldı diye kullanamıyorsanız, o parçayı ölçüsüne göre yeniden üretiyoruz.</p>
<p>Uzaktan kumandanın pil kapağı kaçtı, ses sisteminin düğmesi koptu, modemin ayağı kırıldı, cihazın kapağını tutan minik klips ikiye ayrıldı... İçindeki elektronik gayet iyi durumda, ama o bir tek parça bulunamadığı için koca cihaz çekmecede bekliyor. Bunu çok yaşıyorsunuz, çünkü bu parçalar hiçbir zaman ayrı satılmaz: üretici cihazı komple değiştirmenizi bekler, servis "yedeği yok" der, internette aradığınızda tam o modelin parçası hiçbir yerde çıkmaz.</p>
<p>İşte tam bu boşluğu dolduruyoruz. Elinizdeki kırık parçayı ya da onun takıldığı yeri esas alıp, birebir uyan yenisini üretiyoruz. <strong>Cihaz düğmesi, klipsi, pil kapağı, gövde muhafazası, montaj braketi, ayak, tırnak, kılavuz</strong> — küçük ve bulunması imkânsız plastik parçalar bizim işimiz. Yeni parça eski deliklere oturur, aynı yere geçer, cihaz yeniden çalışır hale gelir.</p>
<p>Markası, modeli, yaşı fark etmez. Parça artık üretilmiyor olsa bile elimizdeki örnekten ya da ölçüden yola çıkarız. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı (kırık parçaları bir arada) veya takıldığı cihazı kargoyla bize gönderin. Parça tamamen kaybolduysa, takılacağı yerin fotoğrafını ve kaba ölçülerini paylaşmanız yeterli.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçer, kırık uçları ve montaj noktalarını çıkarırız. Nereye, nasıl oturduğunu netleştirip size teyit ederiz.</li>
<li><strong>Üret</strong> — Onaydan sonra doğru malzemeyle üretip adresinize yollarız. Takın, cihaz çalışsın.</li>
</ol>
<h2>Doğru malzeme</h2>
<p>Her parça aynı plastikten üretilmez; nereye takılacağına göre seçeriz.</p>
<ul>
<li><strong>Standart / iç mekân parçaları</strong> (kumanda kapağı, düğme, iç klips): dengeli ve temiz malzeme yeterli.</li>
<li><strong>Isıya, neme, UV'ye maruz kalan yerler</strong> (dış gövde, havalandırma yakını, priz/adaptör muhafazası): PETG, ASA veya PC gibi ısı ve dış koşula dayanıklı malzemeler.</li>
<li><strong>Yük taşıyan, sürekli takılıp çıkan, zorlanan parçalar</strong> (menteşe, taşıyıcı braket, gerilmeye çalışan klips): karbon veya cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet.</li>
</ul>
<p>Renk konusunda <strong>farklı renk seçenekleri</strong> sunuyoruz; parçayı cihazın rengine yakın üretmeye çalışırız. Aynı mantığı <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parçalarında</a> da uyguluyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar <strong>yük dışı muhafaza, kapak, düğme ve montaj klipsleridir</strong> — cihazı bir arada tutan, örten, konumlandıran parçalar. Isı üreten güç elektroniğine (trafo, güç katı, ısınan adaptör içi) doğrudan temas eden bir parça söz konusuysa, kullanacağınız yeri bize söyleyin; orada malzemenin ısı sınırı vardır ve gerekiyorsa ısıya dayanıklı sınıfa (PC gibi) yönlendirir, olmayacaksa açıkça söyleriz. Elektriksel yalıtım kritik bir noktaysa bunu baştan konuşuruz. Sözü olmayan işi almayız; parçanız çalışacağı yere göre doğru çözüme oturur.</p>
<p>Örnek parça elinizde yoksa <a href="/numuneye-gore-plastik-parca-uretimi/">numuneden üretim</a> yöntemiyle, hiç bulunamayan bir parça arıyorsanız <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça üretimi</a> sayfamızla ilerleyebilirsiniz. Kablo yönetimi için <a href="/olcuye-ozel-kablo-kanali-organizer-uretimi/">ölçüye özel kablo kanalı ve organizer</a>, uçan ve uzaktan kumandalı modeller için <a href="/drone-rc-model-plastik-parca-uretimi/">drone ve RC model parça üretimi</a> sayfalarına geçebilirsiniz. Malzeme seçimini derinlemesine görmek için <a href="/malzeme-rehberi/">malzeme rehberine</a> bakın.</p>
<h2>Sipariş</h2>
<p>Siparişi iki şekilde verebilirsiniz. Siteden <strong>kartla online ödeme</strong> yaparak doğrudan başlatabilir; ölçü danışmanlığı, özel iş ve parçanızın fotoğrafını göndermek için <strong>WhatsApp +90 545 138 6526</strong> hattından bize yazabilirsiniz. Kırık parçanın fotoğrafını atın, uyup uymayacağını birlikte netleştirelim, üretip yollayalım.</p>""")


def _motosiklet_plastik_parca_ozel_uretim():
    return (u"""<h1>Motosikletin Bulunamayan Plastik Parçasını Üretelim</h1>
<p class="lead">Grenajı çatlamış, klipsi kırılmış, ayna kapağı düşmüş — bayi "o parça artık gelmiyor" diyorsa, o parçayı ölçüsüne göre yeniden üretiyoruz.</p>
<p>Motosiklette en çok kaybolan şey pahalı bir mekanik parça değil; küçük ama olmazsa olmaz bir plastik detaydır. Grenaj klipsi kırılır, panel oynar, titreşim başlar. Ayna kapağı ya da muhafaza kaybolur, açıkta kalan yuva çirkin durur. Eski ya da az satan bir modelde bu parçaların muadili çoğu zaman hiçbir yerde bulunamaz; bulsanız bile komple grenaj takımı almaya zorlanırsınız. Tek ihtiyacınız olan o küçük parçadır.</p>
<p>Biz tam da bu noktada devreye giriyoruz. Elinizdeki kırık parçayı, sökülmüş yuvayı ya da ölçülerinizi bize iletirsiniz; biz o parçayı milimetrik olarak, motosikletinizin gerçek geometrisine uygun şekilde özel üretiriz. Piyasada karşılığı olmayan grenaj klipsi, panel tutucu, ayna kapağı ve muhafaza gibi parçalar için <strong>motosiklet plastik parça özel üretim</strong> yaklaşımımız, "yok" cevabına takılıp kalmanızı önler. Marka veya model fark etmez; parçanın kendisi elimize ölçüyle ulaştığı sürece üretilebilir.</p>
<p>Prensibimiz basit: <strong>Ölçü sizden, üretim bizden.</strong> Kırık grenaj klipsi yaptırma ya da bulunamayan motosiklet parçası üretimi ihtiyacınızı, tahmine değil gerçek ölçüye dayandırırız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da sökülmüş parçayı, varsa eski parçanın fotoğraflarını ve takıldığı yeri bize iletin. Parça elinizde yoksa yuvanın ölçülerini paylaşın.</li>
<li><strong>Ölç</strong> — Deliği, klips mesafesini, kalınlığı ve montaj noktalarını netleştiririz; oturması gereken yere göre toleransı belirleriz.</li>
<li><strong>Üret</strong> — Parçayı ölçünüze göre üretir, kargoyla adresinize göndeririz. Takıp yerine oturttuğunuzda iş biter.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li>Kırık grenaj/panel klipslerinde <strong>klips genişliği, tırnak mesafesi ve dişi-erkek geçme toleransı</strong></li>
<li>Ayna kapağı ve muhafazalarda <strong>dış hat, derinlik ve montaj kulakçıklarının konumu</strong></li>
<li><strong>Delik çapı ve vida yuvası</strong> — mevcut cıvata/klips ölçünüze göre</li>
<li><strong>Kalınlık ve et payı</strong> — titreşimde çıtırdamayacak sıkılıkta oturma</li>
<li><strong>Farklı renk seçenekleri</strong> — mat siyah başta olmak üzere gövdeye yakın tonlar</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç tarafta, güneş ve ısı görmeyen tutucu/klips gibi parçalarda standart dayanıklı malzeme yeterlidir. Motorun yanına yakın, güneş altında kalan ya da yağmura/neme maruz kalan dış panel, ayna kapağı ve muhafazalarda <strong>ısı ve UV'ye dayanıklı ASA, PETG veya PC</strong> kullanırız — açıkta sararmaz, kırılganlaşmaz. Yük binen, sürekli zorlanan montaj noktalarında ise <strong>karbon ya da cam fiber takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli seçeneğe çıkarız.</p>
<p>Aynı mantık farklı araç plastiklerinde de geçerli; <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim ve klips parçalarında</a> da aynı ölçüye-özel yaklaşımı uyguluyoruz. Hangi malzemenin hangi koşula uygun olduğunu <a href="/malzeme-rehberi/">malzeme rehberimizde</a> görebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar yük taşımayan trim, kapak, klips ve muhafaza parçalarıdır; dış gövde estetiği ve montaj işlevi içindir. Motor, süspansiyon ya da taşıyıcı gövde gibi yapısal yük altındaki metal parçaların yerini almaz. Güneş ve ısı söz konusuysa doğru malzemeye (ASA/PETG/PC) yönlendirir, beklentiyi baştan net koyarız. Bu netlik, taktığınız parçanın işini görmesi içindir.</p>
<p>Motosikletiniz için özel bir parça mı gerekiyor, model belirsiz mi? <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parça üretimi</a> ya da <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre üretim</a> sayfalarımız da yol gösterir.</p>
<h2>Sipariş</h2>
<p>Siteden kartla online ödemeyle sipariş verebilir, dilerseniz parçanızı ve ölçünüzü <strong>WhatsApp +90 545 138 6526</strong> hattından iletebilirsiniz. Kırık parçanın fotoğrafını gönderin; üretilebilirliğini ve seçenekleri birlikte netleştirelim. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_huni_uretimi():
    return (u"""<h1>Ölçüye Özel Huni Üretimi — Ağız ve Uç Ölçünüze Göre</h1>
<p class="lead">Standart huninin girmediği dar, eğik veya derin ağızlara; ağzın ve akıtma ucunun tam ölçüsüne göre huni üretiyoruz.</p>
<p>Piyasadaki hazır huniler tek beden mantığıyla satılır: uç çok kalın gelir, ağza oturmaz, dolum sırasında yarısı dışarı taşar. Dar bir depo ağzına, eğik bir dolum boğazına ya da özel bir hortum çapına denk gelen huniyi çoğu zaman rafta bulamazsınız. Biz de tam bu noktada devreye giriyoruz: parçanın gireceği ağzı ve akıtma ucunun oturacağı çapı ölçün, huniyi o ölçüye göre üretelim.</p>
<p>Mutfakta dar ağızlı şişeye dolum yapan, yağ ve yakıt aktarımında damlatmadan doldurmak isteyen, laboratuvarda belirli bir çapa yönlendirme yapan ya da sıkışık bir alanda açılı bir ağza ulaşmaya çalışan herkes için mantıklı. <strong>Plastik huni yaptırma</strong> ihtiyacınızı "yaklaşık uyar" değil, milimetrik ölçüyle karşılıyoruz.</p>
<p>İster elinizde örnek bir huni olsun ister sadece ağız ve uç ölçüleri; <strong>özel ölçü huni</strong> talebinizi ölçüden üretime taşıyoruz. Ölçüyü kargoyla ya da fotoğrafla iletin, üretip size gönderelim.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki örnek huniyi, dolum yaptığınız ağzın fotoğrafını ya da ölçülerini WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Ağız çapını, akıtma ucunun gireceği deliği/hortumu ve gereken koni yüksekliğini birlikte netleştirelim.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip kargoyla gönderelim. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Standart bir kalıp değil, sizin ölçünüze göre şu ayarları yapıyoruz:</p>
<ul>
<li><strong>Ağız çapı (mm)</strong> — geniş toplama ağzından dar boğaza, ihtiyacınıza göre</li>
<li><strong>Koni yüksekliği (mm)</strong> — sığ ve hızlı ya da uzun ve kontrollü akış</li>
<li><strong>Akıtma ucu iç çapı ve boyu (mm)</strong> — hangi ağza ya da hortuma gireceğine göre</li>
<li><strong>Açılı uç kesimi (0–60°)</strong> — dar ve eğik ağızlara rahat oturması için ucu düz ya da açılı kesiyoruz</li>
<li><strong>Glık-glık önleyici hava kanalı (anti-glug)</strong> — dolum sırasında hava kilidini ve fışkırmayı önler</li>
<li><strong>İç yönlendirici kanat</strong> — akışı ortalar, taşmayı azaltır</li>
<li><strong>Asma deliği</strong> — kancaya ya da çiviye asıp saklamak için</li>
<li><strong>Farklı renk seçenekleri</strong> — kullanım alanınıza uygun renklerle</li>
</ul>
<p><strong>Dar ağız dolum hunisi</strong> mi, <strong>yağ-yakıt dolum hunisi üretimi</strong> mi; hangisi olursa olsun ucu ve ağzı işin geometrisine göre biçimlendiriyoruz.</p>
<h2>Doğru malzeme</h2>
<p>Kullanım yerine göre doğru plastiği seçiyoruz. Standart iç-mekan kullanımı için sağlam ve temiz bir gövde; gıda teması, ısı, güneş ve nemin olduğu koşullarda ise <strong>PETG, ASA veya PC</strong> merdivenine çıkıyoruz. Yüksek mukavemet gereken zorlu işlerde <strong>karbon veya cam fiber takviyeli (PA-CF / PA-GF)</strong> seçenekleri var. Hangi sıvı ve hangi ortam olduğunu söyleyin, malzemeyi ona göre yönlendirelim. Malzeme kararında yol göstermesi için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfamıza bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Huni hafif kullanım parçasıdır: sıvıyı yönlendirmek, dolum ve aktarma yapmak için idealdir. Ucu düz ya da 60°'ye kadar açılı kesebiliriz; ancak bükük veya eğri boyunlu (S kıvrımlı) huni üretmeyiz — gövde ve uç düz eksende çalışır. Aşındırıcı kimyasal ya da yüksek sıcaklıkta sürekli temas söz konusuysa önce malzemeyi netleştirir, sınırı açık söyleriz. Amacımız işe yarayan, ölçüsüne oturan bir parça.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ya da örnek parçanızı iletin, ölçüye özel üretip gönderelim. <a href="/">Siteden</a> kartla online ödeme yapabilir; ölçü danışması ve özel iş için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>.</p>
<p>Benzer ölçüye özel işler: <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> ve elinizdeki örnekten çoğaltma için <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a>.</p>""")


def _olcuye_ozel_izgara_petek_uretimi():
    return (u"""<h1>Ölçüye Özel Izgara, Menfez ve Petek Panel Üretimi</h1>
<p class="lead">Boşluğuna tam oturan menfezi, ızgarayı ya da petek paneli ölçüye özel üretiyoruz — piyasada hazır bedeni bulunmayan yeri milimetrik kapatırız.</p>
<p>Havalandırma menfezi kırılmış, dolap arkasındaki fan kapağı boşta kalmış, gider ızgarası ölçü tutmuyor ya da çekmece içine filtre paneli lazım — ve gittiğiniz her yerde "standart bu kadar, sizin ölçü yok" cevabı. Standart bir menfez sizin boşluğunuzu 3-5 mm açık bırakınca da iş görmez: ya toz kaçar, ya hava düzgün yönlenmez, ya da paneli zorla kesip bozarsınız.</p>
<p>Biz tam tersini yaparız: ölçü sizden, üretim bizden. Boşluğun enini, boyunu ve derinliğini siz verirsiniz; menfezi, ızgarayı ya da petek paneli o boşluğa oturacak şekilde üretiriz. Panjur açısından delik şekline, çerçeve formundan montaj tipine kadar her ayrıntı sizin yerinize göre belirlenir.</p>
<p>İster tekli bir kayıp parça olsun ister birkaç adet aynı panel — ölçüsünü alır, doğru malzemeden üretir, kargoyla adresinize yollarız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki kırık menfezin/ızgaranın fotoğrafını ya da kapatmak istediğiniz boşluğu WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Boşluğun en × boy × derinliğini ve varsa montaj deliği aralığını birlikte netleştiririz.</li>
<li><strong>Üret</strong> — Onayınızın ardından ölçüye özel üretir, kargoyla göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Tip:</strong> panjur (hava yönlendirmeli, kanat açısı -45° / +45°), delikli desen ya da kör kapak</li>
<li><strong>En × boy × derinlik / kalınlık (mm):</strong> boşluğunuza tam oturacak ölçü</li>
<li><strong>Delik / göz şekli:</strong> petek, yuvarlak, kare, sekizgen, beşgen, üçgen</li>
<li><strong>Çerçeve / taban şekli:</strong> dikdörtgen, elips/yuvarlak, altıgen</li>
<li><strong>Montaj:</strong> geçme yuvası (insert) ya da vida deliği (M2–M10)</li>
<li><strong>Mod:</strong> delikli (perfore/filtre) ya da kabartma desen</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<p>Somut örnek: dolap havalandırması için altıgen çerçeveli, petek gözlü, geçmeli bir panel; ya da fan önüne yuvarlak kör kapak; ya da gider için kare gözlü, M4 vida delikli dikdörtgen ızgara — hepsi sizin ölçünüze göre.</p>
<h2>Doğru malzeme</h2>
<p>İç mekân, kuru ortamda kullanılacak bir menfez için standart malzeme yeter. Isı, nem, UV ya da dış hava alan yerlerde (mutfak, banyo, tekne, dış cephe menfezi) <strong>PETG, ASA ya da PC</strong> gibi ısıya ve dış koşullara dayanıklı malzemeye geçeriz. Yüksek mukavemet, tokluk gereken panellerde ise <strong>karbon veya cam fiber takviyeli (PA-CF / PA-GF)</strong> malzeme kullanırız. Rengi de işinize göre seçersiniz — farklı renk seçenekleri mevcut.</p>
<p>Menfez sadece bir örnek: <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parçalarını</a> ve <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips parçalarını</a> da aynı mantıkla ölçüye özel üretiriz. Hangi malzemenin hangi işe gittiğini <a href="/malzeme-rehberi/">malzeme rehberinde</a> ayrıntılı anlattık.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz menfez, ızgara ve petek paneller hafif kullanım ve yük-dışı uygulamalar içindir: havalandırma, hava yönlendirme, toz/filtre tutma, gider ızgarası, dekoratif panel gibi. Üzerine çıkılacak, ağırlık taşıyacak ya da yapısal yük binecek bir ızgara ararsanız bu parçalar o iş için değildir. Nereye takacağınızı söyleyin, o kullanıma göre doğru malzemeye yönlendirelim.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ve tipini netleştirelim: menfezinizi, ızgaranızı ya da petek panelinizi ölçüye özel üretip gönderelim. <a href="/">Siteden</a> kartla online ödeyebilir ya da WhatsApp'tan yazıp özel ölçü/üretim danışmanlığı alabilirsiniz: <strong>+90 545 138 6526</strong>.</p>
<p>Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_klips_kelepce_uretimi():
    return (u"""<h1>Ölçüye Özel Klips, Kelepçe ve Kablo Bağı Üretimi</h1>
<p class="lead">Piyasada tam çapını bulamadığınız klips, kelepçe ve kablo bağını ölçünüze özel üretiyoruz — siz ölçüyü verin, parça size göre çıksın.</p>
<p>Boruyu, hortumu, kabloyu ya da mili tutması gereken parça çoğu zaman "yaklaşık" gelir: 18 mm ararsınız, rafta 16 ile 20 vardır; biri boşta oynar, öteki geçmez. Kırılan orijinal kelepçenin muadili hiç yoktur ya da koca bir set almadan tek parça satılmaz. Sonuçta ya zorlayıp kırarsınız ya da bant, kablo bağı, tel gibi geçici çözümlerle idare edersiniz.</p>
<p>Bizim yaptığımız iş tam da bu boşluğu kapatmak. Tuttuğu parçanın gerçek çapını, kelepçenin genişliğini ve nasıl geçmesini istediğinizi alıp, o ölçüye birebir oturan klips veya kelepçeyi üretiriz. "Ölçü sizden, üretim bizden." Standart bir katalogdan seçmezsiniz; parça sizin milimetrenize göre biçimlenir.</p>
<p>Elinizde numune varsa daha da net: eski, kırık kelepçeyi kargoyla gönderin, ölçüsünü çıkarıp yenisini üretip yollayalım. Numune yoksa kumpasla aldığınız çap ve genişlik ölçüleri yeterli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da yetersiz parçanızı gönderin veya bağlanacak boru/kablo/mil çapını ölçüp bize iletin.</li>
<li><strong>Ölç</strong> — Çapı, genişliği ve geçme biçimini netleştiririz; gerekiyorsa doğru tipi birlikte seçeriz.</li>
<li><strong>Üret</strong> — Ölçünüze özel klips/kelepçeyi üretir, adresinize kargolarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Bağlanacak boru / kablo / mil çapı (mm)</strong> — tutması gereken parçanın gerçek çapına göre üretim.</li>
<li><strong>Kelepçe tipi</strong> — açık (geçmeli), kapalı (tam sarma) ya da vidalı sıkma; kullanımınıza göre seçilir.</li>
<li><strong>Genişlik ve et kalınlığı</strong> — daha ince ve hafif mi, yoksa daha geniş ve dolgun mu olsun.</li>
<li><strong>Geçme sıkılığı</strong> — sıkı geçme (yerinden oynamasın) veya normal (kolay tak-çıkar).</li>
<li><strong>Montaj / vida deliği (isteğe bağlı)</strong> — yüzeye vidalanacaksa M ölçüsüne göre delik ekleriz.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür yerlerde ortama uyum için renk seçebilirsiniz.</li>
</ul>
<p>Aynı mantıkla üretilen yakın işler için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips ve parça üretimi</a> ile <a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel bağlantı ve konektör</a> sayfalarına da bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç mekan, kuru ve ılıman kullanımda standart malzeme yeterlidir. Motor bölmesi, güneş altı, dış cephe, nem ya da deniz koşulunda ısıya ve UV'ye dayanıklı <strong>PETG, ASA veya PC</strong> öneririz. Zorlu, sürekli gerilim gören noktalarda ise cam/karbon fiber takviyeli <strong>PA-GF / PA-CF</strong> ile yüksek mukavemetli üretim yaparız. Hangi koşulda kullanacağınızı söyleyin, doğru malzemeye birlikte karar verelim. Detay için <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: klips ve kelepçeler <strong>yük taşıyan bağlantı değildir</strong>. İşleri tutmak, hizada sabitlemek, oynamayı önlemek — yani yük-dışı, düşük ila orta tutma kuvvetidir. Ağır çekme, asma ya da taşıyıcı bir bağlantı arıyorsanız bu doğru parça değildir; bunu baştan söyler, sizi zorlama altında çalışan uygun bir çözüme yönlendiririz. Amaç, elinize tam oturan ama beklentiyi de karşılayan bir parça çıkarmak.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödeyerek doğrudan sipariş verebilirsiniz. Ölçü danışmak, numune göndermek ya da özel bir iş konuşmak isterseniz WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Çapınızı ve tipini iletin, ölçünüze özel klips/kelepçenizi üretip gönderelim.</p>""")


def _olcuye_ozel_kablo_kanali_organizer_uretimi():
    return (u"""<h1>Ölçüye Özel Kablo Kanalı, Yönlendirici ve Organizer Üretimi</h1>
<p class="lead">Standart kesitte bulamadığınız kablo kanalını ölçünüze göre üretiyoruz: kaç kablo geçecekse, nereye oturacaksa ona göre.</p>
<p>Masanın altında dağılan şarj kabloları, panoda birbirine giren besleme hatları, araç içinde sabitlenmeyen tesisat, atölyede ayakaltındaki uzatmalar... Piyasadaki hazır kablo kanalları hep bir "standart" kesitte gelir; sizin boşluğunuza ya çok büyük ya çok küçük olur, kanal sayısı tutmaz, montaj yeri uymaz. Aradığınızı bulamayınca ya idare edersiniz ya da olmayacak bir parçayı zorlarsınız.</p>
<p>Biz işi tersten kuruyoruz: ölçü sizden, üretim bizden. Kablo kanalını, yönlendiriciyi ya da masa/pano organizerini <strong>sizin boşluğunuza ve kablo sayınıza göre</strong> tasarlayıp üretiyoruz. Kaç göz istiyorsanız, hangi uzunlukta, kapaklı mı açık mı — hepsi size özel çıkıyor. Böylece kablolar oynamaz, kanal tam oturur, görüntü toplanır.</p>
<p>İster tek bir masa düzenleyici olsun, ister pano içine birkaç metre özel kanal — adet fark etmez. Ölçüyü siz verin, üretip kargoyla gönderelim.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Nereye takılacağını anlatın: masa altı, pano rayı, araç konsolu, atölye duvarı. Varsa mevcut parçanın fotoğrafını ya da boşluğun ölçüsünü iletin.</li>
<li><strong>Ölç</strong> — Uzunluk, genişlik, yükseklik ve kaç kablo geçeceğini birlikte netleştiririz. Giriş/çıkış ağzının nereye geleceğini belirleriz.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip kargoyla adresinize yollarız. Elinize takıp kullanacağınız hale gelmiş gelir.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Uzunluk × genişlik × yükseklik (mm)</strong> — boşluğunuza tam oturan kesit, ara ölçü dahil</li>
<li><strong>Kanal / göz sayısı</strong> — kaç kablo grubunu ayrı tutmak istiyorsanız ona göre bölmeli</li>
<li><strong>Kapaklı ya da açık</strong> — klipsli kapakla kabloları gizleyin, ya da hızlı erişim için açık bırakın</li>
<li><strong>Montaj biçimi</strong> — yapışkanlı, vidalı ya da geçmeli; yüzeyinize hangisi uyuyorsa</li>
<li><strong>Kablo giriş/çıkış ağzı ve çapı</strong> — kablonun gireceği-çıkacağı yer ve genişliği size göre</li>
<li><strong>Farklı renk seçenekleri</strong> — beyaz masaya, koyu panoya ya da araç içine uyum</li>
</ul>
<p>Belirsiz "her şeyi yaparız" değil; bunlar gerçekten ayarladığımız değerler. Ölçüyü söyleyin, ona göre çıksın.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi kullanım yerine göre seçeriz. İç mekan, masa üstü ve normal oda koşulu için standart dayanıklı malzeme yeterlidir. Araç içi, cam kenarı, dış hava ya da nemli ortam söz konusuysa ısıya ve UV'ye dayanıklı <strong>PETG, ASA ya da PC</strong>'ye geçeriz — güneşte sararmaz, sıcakta yumuşamaz. Sürekli darbe alan ya da yük gören bir noktada tutuluyorsa <strong>karbon/cam fiber takviyeli PA-CF / PA-GF</strong> ile yüksek mukavemetli üretiriz. Renk için farklı seçenekler sunarız.</p>
<h2>Dürüst sınır</h2>
<p>Kablo kanalı ve organizer, kabloları düzenleyen <strong>hafif, yük-dışı</strong> bir parçadır. Kabloyu toplar, yönlendirir, yerinde tutar; ama üstüne çıkılacak, ağırlık taşıyacak ya da yapısal yük binecek bir eleman değildir. Klipsli kapak ve geçmeli montaj düşük–orta tutuş içindir. Ağır sabitleme ya da taşıyıcı gereken yerde bunu baştan söyler, doğru çözüme yönlendiririz. Ne işe yarayıp yaramadığını açık söylemek bizim için güvenin temeli.</p>
<p>Kablo yönetiminin yanında yük-dışı hafif profil ve beam gibi parçalar için <a href="/olcuye-ozel-profil-beam/">ölçüye özel profil ve beam üretimi</a> sayfasına, cihaz içi plastik parçalar için <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a> sayfasına, malzeme seçimini derinlemesine görmek için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Kablo kanalınızı, yönlendiricinizi ya da organizerinizi ölçüye özel üretip gönderelim.</p>
<ul>
<li><strong><a href="/">Site üzerinden</a>:</strong> kartla online ödemeyle sipariş verin, üretip kargoyla yollayalım.</li>
<li><strong>WhatsApp:</strong> ölçü danışmak ya da özel iş için <strong>+90 545 138 6526</strong> — boşluğunuzu anlatın, birlikte netleştirelim.</li>
</ul>""")


def _olcuye_ozel_mentese_uretimi():
    return (u"""<h1>Ölçüye Özel Menteşe ve Reze Üretimi</h1>
<p class="lead">Kırılan menteşenizin ölçüsünü verin, birebir muadilini üretip kargoyla gönderelim.</p>
<p>Dolabın kapağı bir sabah elinizde kalır, kutunun kilit mekanizması oynar, eski bir cihazın menteşesi çatlar. Sonra başlar arayış: hırdavatçıda yok, aynı ölçü hiçbir yerde çıkmıyor, çıkan da ya bir milim büyük ya delikleri tutmuyor. Piyasada bulunamayan menteşe yüzünden koca bir kapağı, dolabı ya da cihazı çöpe atmak zorunda kalmak can sıkar. Oysa çözüm çoğu zaman tek bir küçük parçadır.</p>
<p>PRUVO tam burada devreye girer. <strong>Ölçüye özel menteşe üretimi</strong> işimizin merkezinde: kanat boyunuzu, delik aralığınızı ve pim çapınızı verirsiniz, biz o parçayı milimetrik olarak üretiriz. Standart kalıplara sıkışmadığımız için <strong>bulunamayan menteşe</strong> dediğiniz parça bizde ölçüye göre yeniden hayat bulur. İster tek bir dolap menteşesi olsun, ister eski bir sandığın özel kanatlı rezesi.</p>
<p><strong>Plastik menteşe yaptırma</strong> ihtiyacı olan herkes için akış aynı: mevcut parçayı ya da ölçülerini bize iletirsiniz, gerisini biz hallederiz. Kırık parçanın fotoğrafı ve birkaç ölçü çoğu zaman yeterlidir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık menteşeyi ya da ölçülerini bize gönderin. Elinizdeki parçanın fotoğrafı ve delik düzeni işi büyük ölçüde çözer.</li>
<li><strong>Ölç</strong> — Kanat boyu, genişlik, pim çapı ve vida deliği aralığını netleştirir, size uygun malzemeyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra parçayı ölçünüze özel üretir, kargoyla adresinize yollarız. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p><strong>Özel ölçü menteşe</strong> demek, hazır rafta olmayan her detayı sizin parçanıza göre kurmak demek. Ayarladığımız gerçek seçenekler:</p>
<ul>
<li><strong>Kanat (yaprak) boyu × genişliği</strong> — kırık parçanın birebir ölçüsünde, milimetrik</li>
<li><strong>Pim/mil çapı</strong> — menteşenin döndüğü mil ölçüsüne göre</li>
<li><strong>Vida deliği sayısı ve aralığı</strong> — mevcut delik düzeninize oturacak şekilde</li>
<li><strong>Açılım açısı</strong> — 90°, 180° ya da kapağınızın gerektirdiği özel açı</li>
<li><strong>Kanat kalınlığı</strong> — hafiften daha sağlam gövdeye, kullanım yerine göre</li>
<li><strong>Farklı renk seçenekleri</strong> — mobilyanıza ya da cihazınıza yakın tonlarda</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Her menteşe aynı koşulda çalışmaz, malzemeyi ona göre seçeriz. İç mekân dolap ve kutu menteşelerinde standart dayanıklı malzeme yeterlidir. Nem, ısı ya da güneş gören yerlerde (mutfak, banyo, dış kapaklar) PETG, ASA veya PC gibi ısı ve UV'ye dayanıklı malzemelere geçeriz. Sık açılıp kapanan, daha çok zorlanan menteşelerde ise karbon ve cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Aynı mantık <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> tarafında da geçerli; hangi malzemenin nereye gittiğini <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında açıkladık.</p>
<h2>Dürüst sınır</h2>
<p>Menteşe, doğası gereği yük taşıyan değil, hareket veren bir parçadır. Bizim ürettiğimiz menteşeler yük-dışı ve düşük–orta zorlanma için doğru çözümdür: dolap kapağı, kutu, çekmece, cihaz kapağı, hafif kanatlar. Ağır bir odun kapısını taşıyacak menteşeyi ya da yük taşıyan bir reze sistemini plastikten üretmeyiz; orası metalin işidir. Parçanızın çalışacağı yeri bize anlatın, uygun değilse baştan söyleriz. Sabit montaj ve bağlantı ihtiyacında ise <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a> tarafına bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Ölçülerinizi ilettikten sonra siparişinizi doğrudan <a href="/">sitemizden</a> kartla online verebilirsiniz. Emin olamadığınız bir ölçü, delik düzeni ya da malzeme varsa önce danışın: WhatsApp <strong>+90 545 138 6526</strong>. Kırık menteşenin fotoğrafını ve ölçülerini gönderin, birebir muadilini üretip yollayalım.</p>""")


def _olcuye_ozel_kulp_tutamak_uretimi():
    return (u"""<h1>Ölçüye Özel Kulp, Tutamak ve Kol Üretimi</h1>
<p class="lead">Delik arası tutmayan ya da modeli artık bulunamayan kulbu, ölçünüze göre üretip kargoyla gönderiyoruz.</p>
<p>Çekmecenin, dolabın ya da bir cihazın kulbu kırıldığında iş çoğu zaman tek bir parçada tıkanır: mağazadaki kulplar güzel ama vida delikleri arası mesafe sizinkiyle uyuşmaz, ya da o modelin üretimi çoktan kalkmıştır. Eski deliklere yeni delik açmak, mobilyayı sabitleyip durmak, "yaklaşık olsun" demek çözüm değil. Siz aynı delik aralığını, aynı formu ve doğru vida ölçüsünü istiyorsunuz.</p>
<p>Biz bu noktada devreye giriyoruz: <strong>ölçüye özel kulp üretimi</strong> ile parçayı sizin ölçülerinize göre tek tek çıkarıyoruz. Kırık kulbu ya da elinizdeki eş parçayı referans alıyor; delik arası mesafeyi, boyu ve formu birebir tutuyoruz. Özel tutamak yaptırma, çekmece kulpu üretimi, dolap kulpu ölçüye özel — hepsi aynı mantıkla çalışır: sizin ölçünüz, bizim üretimimiz.</p>
<p>Tek bir kulp da olur, bir mobilya takımının tüm kulpları da. Tekli kırık parça değişiminden, tüm çekmecelere aynı formda seri kol üretimine kadar aynı hassasiyetle ilerliyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık kulbu, eş bir örneği ya da net fotoğraf ve ölçüleri WhatsApp'tan paylaşın.</li>
<li><strong>Ölç</strong> — Vida delikleri arası mesafeyi, toplam boyu, vida ölçüsünü ve formu birlikte netleştiriyoruz.</li>
<li><strong>Üret</strong> — Parçayı ölçünüze göre üretip kargoyla adresinize gönderiyoruz.</li>
</ol>
<p><em>Ölçü sizden, üretim bizden.</em></p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Vida delikleri arası mesafe (mm):</strong> İki montaj deliği arasındaki mesafeyi birebir tutuyoruz; eski delikler aynen oturur.</li>
<li><strong>Form:</strong> Düz çubuk, kavisli, gömme (parmak boşluğu) ya da tekli düğme — kullanımınıza uygun biçim.</li>
<li><strong>Toplam boy ve tutuş kalınlığı:</strong> Elin rahat kavradığı uzunluk ve gövde kalınlığı.</li>
<li><strong>Vida ölçüsü ve deliği (M ölçüsü):</strong> Kullandığınız vidaya uygun delik çapı ve havşa.</li>
<li><strong>Yüzey / kavrama profili:</strong> Düz, tırtıklı ya da hafif kavrama dokusu.</li>
<li><strong>Farklı renk seçenekleri:</strong> Mobilyanıza ya da cihazınıza yakın tonlarda üretim.</li>
</ul>
<p>Ölçüleri paylaşırken kararsız kaldığınız yeri boş bırakın; birlikte netleştiririz.</p>
<h2>Doğru malzeme</h2>
<p>İç mekân, günlük kullanım kulpları için standart malzeme yeterli ve temiz bir sonuç verir. Mutfak, ıslak alan ya da güneş gören yüzeylerde ısı, nem ve UV'ye dayanıklı <strong>PETG, ASA veya PC</strong> öneriyoruz. Sık ve sert çekilen, yüke daha çok maruz kalan kollarda ise <strong>karbon/cam elyaf takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli malzemeye geçiyoruz. Parçanızın çalışacağı yere göre doğru malzemeye sizi yönlendiriyoruz. Aynı mantığın malzeme tarafını <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında ayrıntılı anlattık.</p>
<h2>Dürüst sınır</h2>
<p>Kulp ve tutamaklar <strong>hafif kullanım ve günlük tutuş</strong> için tasarlanır: çekmece açmak, dolap kapağını çekmek, cihazı taşımak. Ağır yük asma, tüm ağırlığın tek kulba bindiği taşıma ya da darbeli zorlama için uygun değildir. Kullanımınızı baştan konuşur, doğru malzemeyle en dayanıklı sonucu birlikte hedefleriz. Beyaz eşya ve cihaz parçalarında benzer değişimler için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfasına, kırılan diğer plastik parçalar için <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasına bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir, ölçü ve form danışmanlığı için WhatsApp hattımızdan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık kulbun fotoğrafını ve delik arası ölçüsünü gönderin; formu netleştirip üretime alalım. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_tapa_kapak_uretimi():
    return (u"""<h1>Ölçüye Özel Tapa, Kapak ve Tıkaç Üretimi</h1>
<p class="lead">Kırılan, kaybolan ya da piyasada hiç bulunmayan tapayı ölçüsüne göre üretiyoruz — ölçü sizden, üretim bizden.</p>
<p>Bir profilin, borunun ya da hazne ağzının tapası zamanla kırılır, kaybolur veya hiç birlikte gelmez. Yedeğini aramaya çıktığınızda ise standart ölçüler tutmaz: çap birkaç milim oynar, geçme ya çok gevşek ya hiç girmez. Nalburda, sanayide, internette dolaşıp "yaklaşık" bir şey bulmak yerine, tam oturan bir parça istersiniz. Biz de tam bunu yapıyoruz.</p>
<p>Kare profil ağzını kapatan bir tıkaç, alüminyum borunun uç kapağı, makine haznesinin diş kapağı, mobilya ayağının tabanı ya da elektronik kutusunun deliğini kapatan bir tapa — hepsi ölçüye özel üretilebilir. Elinizdeki delik ya da ağız ne ise, iç veya dış çapını, geçme tipini ve sıkılığını söylersiniz; parçayı ona göre çıkarırız.</p>
<p>En sık gelen ihtiyaç şu: elde tek bir sağlam örnek var ama eşi yok. O örneği referans alıp aynısını, isterseniz farklı renkte çoğaltabiliriz. Örnek yoksa da sorun değil; ağzın iç/dış çapını ve derinliğini ölçüp bize iletmeniz yeterli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir / ilet</strong> — Kırık tapayı, kapağı ya da kapatılacak ağzı bize gösterin. Ulaşamıyorsanız kargoyla gönderin; uzaktaysanız birkaç net fotoğraf ve ölçü de yeter.</li>
<li><strong>Ölç</strong> — İç ya da dış çapı, derinliği ve geçme sıkılığını netleştiririz. Kritik yüzeyleri birlikte konuşuruz.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip size ulaştırırız. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Standart bir tapayı değil, sizin ağzınıza özel bir parçayı çıkarıyoruz. Somut olarak ayarlanan noktalar:</p>
<ul>
<li><strong>İç ya da dış çap (mm)</strong> — deliğin içine mi girecek, ağzın üstüne mi geçecek, ona göre ölçüye özel</li>
<li><strong>Geçme tipi</strong> — içten geçme, dıştan geçme ya da vidalı (dişli) kapak</li>
<li><strong>Geçme sıkılığı</strong> — sıkı (zor çıkan, kalıcı) ya da normal (elle takıp çıkarılabilen)</li>
<li><strong>Kesit</strong> — yuvarlak, kare, dikdörtgen ya da profil ağzına özel form</li>
<li><strong>Sap / tutma çıkıntısı</strong> — isteğe bağlı, elle kolay çekip çıkarmak için</li>
<li><strong>Farklı renk seçenekleri</strong> — göze uygun, ayırt edici ton seçimi</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Parçanın çalışacağı yere göre malzeme seçiyoruz. İç mekân, kuru ortam ve hafif kullanım için standart, dayanıklı bir malzeme yeterli. Güneş, ısı, nem, deniz koşulu ya da dışarıda kalacak bir tapa söz konusuysa UV ve ısıya dayanıklı PETG, ASA veya PC'ye çıkıyoruz. Sürekli darbe alan, zorlanan ya da yük taşıyan bir uygulamada karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlıyoruz. Hangi malzemenin sizin işinize oturduğunu birlikte netleştirmek için <a href="/malzeme-rehberi/">malzeme rehberine</a> göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Tapa, kapak ve tıkaç bizim için <strong>hafif kullanım</strong> işidir: kapatma, koruma, toz-nem tutma, örtme amaçlıdır. Basınçlı sızdırmazlık, contalama ya da yüksek basınç altında tam kapatma gerektiren yerlerde tapa doğru çözüm değildir — bunun için <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfasına bakın. Ne olacağını olduğundan büyük göstermeyiz; parçayı çalışacağı yere göre doğru malzemeye yönlendiririz.</p>
<p>Bulunamayan başka bir yedek parça mı arıyorsunuz? <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parça özel üretim</a> sayfası tam bu iş için.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü netleştirip üretime alalım. Elinizdeki örneği ya da ağzın ölçülerini iletin; siz onaylayın, biz üretip gönderelim. <a href="/">Siteden</a> kartla online ödeme ile sipariş verebilir, özel iş ve ölçü danışması için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Ölçü sizden, üretim bizden.</p>""")


def _tarim_makinesi_plastik_parca_uretimi():
    return (u"""<h1>Tarım ve Bahçe Makinesi Plastik Parçalarının Özel Üretimi</h1>
<p class="lead">Modeli kalkmış tarım aletinizin kırılan plastik parçasını, elinizdeki örneğe göre ölçüye özel üretiyoruz.</p>
<p>Çapa makinesi, mibzer, pülverizatör, biçme makinesi, sırt atomizörü ya da bahçe traktörü... Bu makinelerin yıllar önce üretilmiş modellerinde bir plastik parça kırıldığında çoğu zaman yedeği artık hiçbir yerde bulunmuyor. Bayi "o model bitti" diyor, sanayide örneği yok, makine tek bir kapak, dişli göbeği ya da bağlantı klipsi yüzünden atıl kalıyor. Oysa parçanın kendisi elinizde — kırık haliyle bile ölçü alınabilir durumda.</p>
<p>İşte tam da bunun için varız. Bize kırık parçanın kendisini ya da net ölçülerini/fotoğrafını gönderin; biz onu birebir çıkarıp, çalıştığı koşula uygun malzemeyle yeniden üretelim. <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parçalarda</a> yaptığımız iş budur: piyasada olmayanı sizin örneğinizden geri getiriyoruz.</p>
<p>Tarım ve bahçe makineleri güneş, UV, nem, toz ve titreşim altında çalışır. Bu yüzden "bir plastik bulalım takalım" mantığıyla değil, parçanın maruz kaldığı dış koşula göre doğru malzemeyi seçerek üretiyoruz. Kaporta altındaki bir bağlantıdan, sürekli güneş gören bir kapağa kadar her parçanın gereği farklıdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eskiyen parçayı, varsa sağlam bir eşini, kargoyla bize gönderin. Parça bulunamıyorsa net fotoğraf ve ölçüler de yeterli.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik çıkarır, kırık/aşınmış yerleri tamamlar, montaj deliklerini ve oturma noktalarını orijinaline göre doğrularız.</li>
<li><strong>Üret</strong> — Onayınızın ardından ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Birebir ölçü</strong> — Delik çapları, vida/cıvata yuvaları, kanal ve tırnak mesafeleri elinizdeki parçaya göre.</li>
<li><strong>Malzeme sınıfı</strong> — Kullanım yerine göre iç mekân plastiğinden dış koşula dayanıklı sınıfa kadar seçim.</li>
<li><strong>Duvar/et kalınlığı</strong> — Aynı parçayı ihtiyaca göre daha sağlam ya da orijinaliyle aynı ölçüde.</li>
<li><strong>Farklı renk seçenekleri</strong> — Makinenin rengine yakın ya da ayırt edici bir tonda.</li>
<li><strong>Adet</strong> — Tek parça ya da atölyeniz/deponuz için küçük seri.</li>
</ul>
<p>Standart bir <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretiminde</a> olduğu gibi, döner aktarım gerektiren yerlerde <a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişli üretimi</a> de yapıyoruz.</p>
<h2>Doğru malzeme</h2>
<p>Malzeme, parçanın nerede çalıştığına göre yükselen bir merdivendir. İç mekânda ya da yükten uzak yerlerde PETG dengeli ve dayanıklı bir tercihtir. Sürekli güneş, UV, nem ve dış hava gören parçalarda ASA ve PC öne çıkar — solmaya ve ısıya direnir. Yük ve tork taşıyan, zorlanan parçalarda ise karbon/cam elyaf takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangisinin uygun olduğunu parçanızın çalıştığı yere göre biz öneririz. Ayrıntı için <a href="/malzeme-rehberi/">malzeme rehberine</a> bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Her parçayı doğru yere yönlendiririz. Kulp, kapak, huni, tapa gibi parçalar hafif kullanım içindir. Klips, kelepçe, menteşe gibi bağlantılar yük-dışı ya da düşük–orta zorlanma için uygundur; kasnak türü aktarımlar düşük–orta yük ve torkta iş görür, ağır tahrik hattının metal parçasının yerini tutmaz. Dişli ve genel parçalarda dayanım, çalışacağı yüke göre değişir. Metal zorunlu ağır tahrik parçasını plastikle değiştirmeyiz — parçanızı en doğru çözüme yönlendirmek işimizin bir parçası.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Siparişinizi <a href="/">siteden</a> kartla online ödemeyle verebilir, kırık parçanızı ölçtürmek ve doğru malzemeyi konuşmak için WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına yazabilirsiniz. Parçayı gönderin, ölçelim, üretip yollayalım.</p>""")


def _mobilya_plastik_baglanti_ayak_parca_uretimi():
    return (u"""<h1>Mobilya Plastik Bağlantı, Ayak ve Kayar Pabuç Üretimi</h1>
<p class="lead">Kutudan çıkan o küçük plastik parça kırıldı ve hiçbir yerde bulamıyorsanız, numunesini bize gönderin; birebir aynısını ölçüye özel üretip yollayalım.</p>
<p>Dolabın, gardırobun, koltuğun ya da masanın montaj kutusunda gelen o minik plastik bağlantı elemanları çoğu zaman ayrı satılmaz. Bir tanesi kırıldığında ya da kaybolduğunda, koca mobilya sırf o parça yüzünden sallanır, kapak kapanmaz, ayak dengesini kaybeder. Marka bu parçaları perakende vermez; benzeri diye alınan muadil de ölçü tutmaz.</p>
<p>Biz tam bu noktada devreye giriyoruz. Elinizdeki kırık parçayı ya da sağlam bir eşini numune olarak alıp, mobilya plastik bağlantı parçası üretimi işini birebir kopya mantığıyla yapıyoruz. Dolap bağlantı parçası özel geometrisiyle, mobilya ayağı yaptırma talebiniz gerçek ölçüsüyle, kayar pabuç üretimi ise yüzeyde sessiz kaymayı sağlayacak formuyla çıkar. Tek adet yeter; bir sürü sipariş etmek zorunda değilsiniz.</p>
<p>Bulunamayan mobilya plastik parça derdinin çözümü, parçayı sıfırdan aramak değil; var olanı ölçüye özel yeniden üretmek. Kanca, geçme dili, tırnak, kayar taban, ayak altlığı, gizli bağlantı pimi... hangisiyse, o parçanın oturması gereken yere tam oturmasını sağlıyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da sağlam parçanın fotoğrafını ve mümkünse birkaç ölçüsünü WhatsApp'tan gönderin; parçayı kargoyla numune olarak da yollayabilirsiniz.</li>
<li><strong>Ölç</strong> — Numuneyi milimetrik ölçüp geometrisini birebir çıkarıyoruz; delik aralığı, geçme payı, kalınlık ve tırnak formu dahil.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip adresinize gönderiyoruz. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li>Numuneden birebir kopya: delik aralığı, geçme dili, tırnak ve kanca formu aynen</li>
<li>Tek adet ya da az sayıda üretim — stok/toptan zorunluluğu yok</li>
<li>Ayak yüksekliği, taban çapı ve oturma açısı sizin mobilyanıza göre</li>
<li>Kayar pabuçta yüzeye uygun kayma tabanı ve sessiz temas formu</li>
<li>Farklı renk seçenekleri (mobilyanızla uyumlu tona yakın)</li>
</ul>
<h2>Doğru malzeme</h2>
<p>İç mekân mobilya parçalarının çoğu için standart, sağlam bir malzeme yeterli olur. Neme, ısıya ya da güneş gören bir yüzeye maruz kalan parçalarda PETG, ASA veya PC gibi dayanıklı malzemelere geçiyoruz. Sürekli yük altında çalışan, gerilen ya da darbe alan bağlantılarda ise cam/karbon fiber takviyeli PA-GF / PA-CF ile yüksek mukavemetli üretim yapıyoruz. Parçanın nerede çalışacağını söyleyin, doğru malzemeye biz yönlendirelim. Malzeme seçimini derinlemesine görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfamıza bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: bu parçalar bağlantı, konumlandırma ve hafif taşıma içindir. Klips, geçme ve menteşe benzeri elemanlar yük-dışı ya da düşük–orta yük içindir; ayak ve altlıklar mobilyanın kendi ağırlığını dengeler, ağır darbe ya da taşıyıcı iskelet görevi görmez. Dolabın tüm yükünü tek bir plastik ayağa bindiren bir kullanım için değil, orijinal parçanın yaptığı işi aynen görmesi için üretiriz. Neyin sınırda olduğunu baştan söyleriz.</p>
<h2>Sipariş</h2>
<p>Numunenizin fotoğrafını ve ölçülerini WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; birlikte netleştirip fiyat verelim. Onay sonrası <a href="/">siteden</a> kartla online ödemeyle siparişinizi tamamlayabilirsiniz.</p>
<p>İlgili olabilecek diğer hizmetlerimiz: <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a>, <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> ve <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a>.</p>""")


def _drone_rc_model_plastik_parca_uretimi():
    return (u"""<h1>Drone ve RC Model İçin Ölçüye Özel Plastik Parça Üretimi</h1>
<p class="lead">Kırılan drone kolunu, RC modelin gövde kapağını ya da iniş takımını bulamıyorsanız; parçayı bize gönderin, ölçüye özel yeniden üretelim.</p>
<p>Drone ve RC model kullananlar aynı sorunu yaşar: bir kaza olur, motor kolu çatlar ya da montaj braketi kırılır; üretici o parçayı artık satmıyordur veya modeliniz zaten piyasadan kalkmıştır. Tek bir küçük plastik parça yüzünden koca bir cihaz rafta bekler. Biz tam da bu noktada devreye giriyoruz: elinizdeki kırık parçadan ya da ölçülerinden yola çıkarak aynısını, çoğu zaman daha dayanıklı malzemeyle üretiyoruz.</p>
<p>Drone gövde kolu, motor yuvası, iniş takımı ayağı, kamera/gimbal braketi, pil kapağı, gövde plakası, RC araç süspansiyon kolu, tampon ve şasi bağlantı parçaları gibi yapısal ve montaj parçalarını ölçünüze göre üretiyoruz. Elimizde parçanın kendisi varsa birebir çıkarırız; yoksa fotoğraf, teknik çizim ya da ölçülerinizle çalışırız.</p>
<p>Hobi kullanıcısı için en kritik denge hafiflik ve mukavemettir. Uçan bir modelde her gram önemlidir ama parça da darbeye dayanmalıdır. Bu yüzden drone ve RC model parçalarında çoğunlukla karbon fiber takviyeli malzemeye (PA-CF) yöneliriz: hafif kalır, bükülmez, kazada seri parçadan daha iyi dayanır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı kargoyla gönderin ya da ölçü/fotoğraf/çizimi WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçer, bağlantı deliklerini ve montaj noktalarını birebir çıkarırız.</li>
<li><strong>Üret</strong> — Doğru malzemeyle üretip adresinize göndeririz. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Parça tipi:</strong> gövde kolu, motor yuvası, iniş takımı, gimbal/kamera braketi, pil kapağı, gövde plakası, RC şasi ve süspansiyon bağlantıları</li>
<li><strong>Ölçü:</strong> kol uzunluğu, delik aks aralığı, vida/cıvata çapı, montaj deseni birebir sizin modelinize göre</li>
<li><strong>Malzeme sınıfı:</strong> iç mekan/standart, ısı-UV dayanımı, yüksek mukavemet (aşağıda detay)</li>
<li><strong>Renk:</strong> farklı renk seçenekleri (aynı modelin sağ/sol kolunu ayırmak için renk kodlaması dahil)</li>
<li><strong>Adet:</strong> tek yedek ya da kaza ihtimaline karşı birkaç kolluk set</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekan parçalarında PETG ile başlarız. Dışarıda, güneş ve nem altında uçan modeller için ısı ve UV'ye dayanıklı ASA veya PC öneririz. Uçuş yükü taşıyan gövde kolu, motor yuvası, iniş takımı gibi parçalarda ise karbon/cam fiber takviyeli malzemeye (PA-CF / PA-GF) geçeriz: en yüksek mukavemet, en düşük ağırlık. Hangi parçanın nereye takılacağını sorar, ona göre yönlendiririz.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: itiş pervanesi ve yüksek devirli uçuş pervanesi ÜRETMİYORUZ. Bunlar hassas balans ve yüksek devir dayanımı ister; plastik üretim burada güvenli değildir ve sizi yanıltmayız. Bizim işimiz yapısal ve montaj parçaları: kol, braket, kapak, iniş takımı, şasi bağlantıları. Braket ve klips tipi bağlantı parçaları yük dışı/düşük-orta zorlama içindir; gövde kolu ve iniş takımını ise kazada tekrar tekrar dayanacak takviyeli malzemeyle veririz. Parçayı çalışacağı yere göre doğru malzemeye yönlendirir, taşıyamayacağı yükü taşır demeyiz.</p>
<p>İlgili sayfalar: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a>, <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a>, <a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel bağlantı ve konektör</a> ve <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir, ölçüye özel işiniz için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık parçanızı gönderin ya da ölçülerinizi iletin; drone ve RC modelinizi tekrar uçuşa hazır hale getirelim. Ölçü sizden, üretim bizden.</p>""")


def _ev_aleti_plastik_disli_parca_uretimi():
    return (u"""<h1>Mutfak Robotu ve Ev Aleti Plastik Dişli/Parça Üretimi</h1>
<p class="lead">Blenderiniz dönmüyor, kıyma makinesinden ses gelip iş görmüyor ya da mikser boşta kalıyorsa suçlu çoğu zaman içerideki küçük plastik dişlidir. İyi haber: cihazı çöpe atmanıza gerek yok, o parçayı ölçünüze göre yeniden üretebiliriz.</p>
<p>Ev aleti plastik dişli üretimi, yedek parçası artık bulunmayan cihazlar için en kestirme çözümdür. Marka servisi "parça yok" dediğinde ya da model eskidiğinde, elinizdeki kırık dişliyi örnek alıp aynı diş sayısı, aynı çap ve aynı mil yatağıyla yeniden yapıyoruz. Mutfak robotu dişli yaptırma, blender dişli üretimi, kıyma makinesi plastik parça veya mikser yedek parça özel talepleri bizim için tipik iştir.</p>
<p>Aradığınız parçayı bulamadıysanız genel <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretimi</a> sayfamıza da bakabilirsiniz; sadece dişli değil, kırılan her küçük plastik parçayı aynı yöntemle ele alıyoruz. Dişlinin kendisine odaklanmak isterseniz <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli üretimi</a> sayfamız üst başvuru noktanızdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık dişliyi veya parçayı kargoyla bize gönderin. Elinizde parça kalmadıysa cihaz marka-modelini ve varsa parça numarasını iletin.</li>
<li><strong>Ölç:</strong> Diş sayısını, dış çapı, mil deliğini ve kanal/kama detaylarını milimetrik ölçeriz. Ölçü sizde değilse örnekten biz çıkarırız.</li>
<li><strong>Üret:</strong> Ölçüye özel üretip test eder, kargoyla adresinize yollarız. Türkiye'nin her yerine gönderiyoruz.</li>
</ol>
<h2>Ölçünüze göre çıkardığımız detaylar</h2>
<ul>
<li>Diş sayısı, modül ve diş profili (parçaya birebir uyacak şekilde)</li>
<li>Dış çap, iç çap ve toplam yükseklik</li>
<li>Mil deliği çapı, kama/kanal veya D-tipi düzleştirme</li>
<li>Bağlantı tırnakları, kertikler ve oturma yüzeyleri</li>
<li>Malzeme ve farklı renk seçenekleri</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekan parçalarında sağlam ve tok malzemelerle (PETG, ASA, PC) çalışırız; ısı, nem ve sürekli kullanım bunlarda sorun çıkarmaz. Sürtünen ve aşınan dişlilerde ise yüksek mukavemetli, karbon veya cam fiber takviyeli malzeme (PA-CF / PA-GF) öneririz — bu grup aşınma dayanımı ve boyutsal kararlılıkta belirgin fark yaratır. Cihazınızın çalışma koşuluna göre doğru malzemeye yönlendiririz. Malzemelerin nerede ne işe yaradığını <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasından ayrıntılı görebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Plastik dişli ve parçalarda dayanım, çalıştığı yüke göre değişir; dürüst konuşmak güven verir. Mutfak robotu, blender, mikser ve kıyma makinesi gibi ev aletlerindeki dişliler genelde düşük–orta tork aralığında çalışır ve bu iş için uygundur. Ağır sanayi tahriki, yüksek tork ya da metalin taşıması gereken sürekli yük söz konusuysa parça plastikle kalıcı çözüm olmaz; böyle bir durumda size baştan söyler, doğru yönlendirmeyi yaparız. Aynı yaklaşımı geniş <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> tarafında da uyguluyoruz.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir ya da parçanızı anlatmak, ölçü danışmak için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık dişlinizin fotoğrafını gönderin, uygunluğunu ve seçenekleri birlikte netleştirelim. Ölçü sizden, üretim bizden.</p>""")


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
    ('piyasada-bulunmayan-yedek-parca-uretimi', 'Piyasada Bulunmayan Yedek Parça Üretimi', 'Üretimden kalkmış, muadili olmayan ya da hiç ayrı satılmayan parçayı numuneden ölçüye özel üretiyoruz. Tek adet, doğru malzeme. Getir, ölçelim, üretelim.', _piyasada_bulunmayan_yedek_parca_uretimi),
    ('kirik-plastik-parca-yaptirma', 'Kırık Plastik Parçanın Yenisini Yaptırma', 'Kırılan plastik parçayı atmayın; numunesinden ölçüye özel yenisini üretiyoruz. Tek adet, kullanım yerine uygun dayanıklı malzeme. Getir, ölçelim, üretelim.', _kirik_plastik_parca_yaptirma),
    ('tek-adet-ozel-parca-uretimi', 'Tek Adet Özel Plastik Parça Üretimi', 'Tek bir parça mı lazım? Minimum sipariş yok. Numune ya da ölçüden tek adet özel plastik parça üretiyoruz, doğru malzemeyle. Getir, ölçelim, üretelim.', _tek_adet_ozel_parca_uretimi),
    ('olcuye-ozel-baglanti-konektor', 'Ölçüye Özel Bağlantı ve Konektör Üretimi', 'Çubuk ve boruları birleştiren konektörü ölçünüze göre üretiyoruz: 2-4 kol, yuvarlak/kare/sekizgen kesit, çap ve açıya göre. Yük-dışı montaj. Getir, ölç, üret.', _olcuye_ozel_baglanti_konektor),
    ('olcuye-ozel-montaj-braketi', 'Ölçüye Özel Montaj Braketi Üretimi', 'Açılı, köşe, düz, T, L veya Y montaj braketini ölçünüze göre üretiyoruz: iç açı, vida deliği düzeni, sağ/sol simetri. Yük-dışı montaj. Getir, ölç, üret.', _olcuye_ozel_montaj_braketi),
    ('olcuye-ozel-profil-beam', 'Ölçüye Özel Profil, Kızak ve Kiriş Üretimi', 'I, T, L, U, kutu, çokgen ya da sigma profil kesitini ölçünüze göre üretiyoruz. Yükseklik, genişlik, et kalınlığı sizden. Yük-dışı/hafif. Getir, ölç, üret.', _olcuye_ozel_profil_beam),
    ('kasnak-olcuye-ozel-uretim', 'Ölçüye Özel Kasnak Üretimi (V/Düz Kayış)', 'V-kayış, düz kayış ve kordon kasnağını numuneden ölçüye özel üretiyoruz: kanal sayısı, dış çap, mil bağlantısı. Düşük-orta yük/tork. Getir, ölç, üret.', _kasnak_olcuye_ozel_uretim),
    ('olcuye-ozel-vida-somun-civata-uretimi', 'Ölçüye Özel Vida, Somun ve Cıvata Üretimi', 'Cıvata, dişli mil, somun ve pulu ölçünüze göre üretiyoruz: metrik/inç/özel diş, kafa ve tornavida ağzı, trapez hareket vidası. Hafif-orta yük. Getir, ölç, üret.', _olcuye_ozel_vida_somun_civata_uretimi),
    ('olcuye-ozel-yay-uretimi', 'Ölçüye Özel Plastik Yay Üretimi', 'Bası yayı ya da dalga/flexure elemanını ölçünüze göre üretiyoruz: serbest boy, dış çap, tel çapı, sarım. Hafif kuvvet/geri dönüş işleri. Getir, ölçelim, üretelim.', _olcuye_ozel_yay_uretimi),
    ('elektronik-cihaz-plastik-parca-uretimi', 'Elektronik Cihaz Plastik Parça Üretimi', "Kırılan düğme, klips, kapak, tutamak ya da muhafazayı numuneden ölçüye özel üretiyoruz. Isı ve UV'ye dayanıklı malzeme. Tek adet. Getir, ölçelim, üretelim.", _elektronik_cihaz_plastik_parca_uretimi),
    ('motosiklet-plastik-parca-ozel-uretim', 'Motosiklet Plastik Parça Özel Üretim', 'Grenaj klipsi, ayna kapağı, muhafaza ya da braket bulunamıyor mu? Motosiklet plastik parçasını numuneden ölçüye özel üretiyoruz. UV/ısıya dayanıklı, tek adet.', _motosiklet_plastik_parca_ozel_uretim),
    ('olcuye-ozel-huni-uretimi', 'Ölçüye Özel Huni Üretimi — Dolum ve Mutfak', 'Mutfak, yağ-yakıt dolumu ya da dar ağızlar için huniyi ölçünüze göre üretiyoruz: ağız çapı, akıtma ucu, açılı uç, glık-glık önleyici hava kanalı. Getir, ölç, üret.', _olcuye_ozel_huni_uretimi),
    ('olcuye-ozel-izgara-petek-uretimi', 'Ölçüye Özel Izgara, Menfez ve Petek Üretimi', 'Havalandırma menfezi, fan kapağı, filtre ızgarası ya da petek paneli boşluğunuza göre üretiyoruz: panjur/delikli/kör, göz şekli, geçmeli ya da vidalı. Getir, ölç, üret.', _olcuye_ozel_izgara_petek_uretimi),
    ('olcuye-ozel-klips-kelepce-uretimi', 'Ölçüye Özel Klips ve Kelepçe Üretimi', 'Kırılan klips ya da bulunamayan boru/kablo kelepçesini ölçünüze göre üretiyoruz: çap, genişlik, açık/kapalı tip, geçme sıkılığı. Yük-dışı. Getir, ölç, üret.', _olcuye_ozel_klips_kelepce_uretimi),
    ('olcuye-ozel-kablo-kanali-organizer-uretimi', 'Ölçüye Özel Kablo Kanalı ve Organizer', 'Masa, pano ya da araç için kablo kanalını ve organizerı ölçünüze göre üretiyoruz: genişlik, kanal sayısı, kapaklı/açık, montaj tipi. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_kablo_kanali_organizer_uretimi),
    ('olcuye-ozel-mentese-uretimi', 'Ölçüye Özel Plastik Menteşe Üretimi', 'Kırılan ya da bulunamayan menteşeyi ölçünüze göre üretiyoruz: kanat boyu, pim çapı, delik düzeni, açılım açısı. Yük-dışı/düşük-orta. Getir, ölç, üret.', _olcuye_ozel_mentese_uretimi),
    ('olcuye-ozel-kulp-tutamak-uretimi', 'Ölçüye Özel Kulp ve Tutamak Üretimi', 'Kırılan çekmece kulpunu, dolap tutamağını ya da cihaz kolunu ölçünüze göre üretiyoruz: delik mesafesi, form, vida ölçüsü. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_kulp_tutamak_uretimi),
    ('olcuye-ozel-tapa-kapak-uretimi', 'Ölçüye Özel Tapa, Kapak ve Tıkaç Üretimi', 'Boru, profil ya da haznenin kayıp tapasını/kapağını ölçünüze göre üretiyoruz: iç/dış çap, geçme sıkılığı, vidalı ya da geçmeli. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_tapa_kapak_uretimi),
    ('tarim-makinesi-plastik-parca-uretimi', 'Tarım Makinesi Plastik Parça Üretimi', 'Traktör, çapa, biçme, ilaçlama ya da bahçe makinesinin bulunamayan plastik parçasını numuneden ölçüye özel üretiyoruz. UV ve dış koşula dayanıklı malzeme.', _tarim_makinesi_plastik_parca_uretimi),
    ('mobilya-plastik-baglanti-ayak-parca-uretimi', 'Mobilya Plastik Bağlantı ve Ayak Parçası', 'Kırılan mobilya bağlantısını, ayağını, kayar pabucunu ya da geçme parçasını ölçünüze göre üretiyoruz. Numune yeter, tek adet. Getir, ölç, üret.', _mobilya_plastik_baglanti_ayak_parca_uretimi),
    ('drone-rc-model-plastik-parca-uretimi', 'Drone ve RC Model Plastik Parça Üretimi', 'Kırılan drone gövdesi, motor kolu, iniş takımı ya da RC model parçasını numuneden ölçüye özel üretiyoruz. Hafif ve dayanıklı malzeme. Getir, ölç, üret.', _drone_rc_model_plastik_parca_uretimi),
    ('ev-aleti-plastik-disli-parca-uretimi', 'Ev Aleti Plastik Dişli ve Parça Üretimi', 'Mutfak robotu, blender, kıyma makinesi ya da mikserin kırılan plastik dişlisini ve parçasını numuneden ölçüye özel üretiyoruz. Yüke göre takviyeli malzeme.', _ev_aleti_plastik_disli_parca_uretimi),
]

# Statik içerik/yasal sayfalar: elle yazılmış, build.py ÜRETMEZ (repo'da commit'li), korunur.
STATIK_SAYFALAR = ["hakkimizda", "iletisim", "sss", "gizlilik"]

# sitemap + deploy.yml yayın-beyaz-listesi için TÜM içerik/yasal slug'lar (statik + ÜRETİLEN).
# Üretilen kısım CONTENT_PAGES'ten TÜRETİLİR = TEK KAYNAK: CONTENT_PAGES'e sayfa eklemek
# sitemap'e VE yayın manifestine (build.py _yayin-icerik-dizinleri.txt) otomatik yansır.
# Eskiden bu liste elle tutuluyordu -> CONTENT_PAGES'e eklenip buraya eklenmeyen sayfa
# sitemap dışı kalıp yayına girmiyordu (sessiz 404). Artık senkron elle DEĞİL.
SITEMAP_SLUGS = STATIK_SAYFALAR + [slug for slug, _baslik, _meta, _fn in CONTENT_PAGES]
