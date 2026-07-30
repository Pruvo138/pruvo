/**
 * URETILMIS DOSYA — ELLE DUZENLEME (elle yapilan degisiklik ilk uretimde KAYBOLUR).
 *
 * KAYNAK: jenerator/urunler/*.json — parametrik ("olcuye ozel", sari seri) urun semalari.
 * URET  : python3 tools/sema-bundle-kapisi.py --yaz
 * KAPI  : python3 tools/sema-bundle-kapisi.py   (deploy.yml'de BLOKLAYICI; liste bayatsa
 *         CI KIRMIZI yanar -> "yeni sema eklendi, import listesi guncellenmedi" penceresi
 *         kapali)
 *
 * NEDEN STATIK IMPORT LISTESI: Worker'da dosya sistemi/glob YOK; wrangler(esbuild) yalniz
 * statik import'lari bundle'a katar. Liste dizinden AYRISIRSA hata SESSIZDIR — sema
 * bulunamayan sari urun kartla tahsil edilemez (shop/src/index.js "parametrik-urun" 400 ->
 * WhatsApp), ayni id'yi tasiyan iki sema ise sessizce YANLIS FIYAT uretir. Kapi ikisini de
 * uretimden ONCE bloklar.
 *
 * Semalar public veri (matematik + aralik); sir icermez (gizlilik: tedarikci izi yok).
 */

import s_kisiye_ozel_jeton_cip_madalyon from "../../jenerator/urunler/kisiye-ozel-jeton-cip-madalyon.json";
import s_olcuye_ozel_baglanti_konektor from "../../jenerator/urunler/olcuye-ozel-baglanti-konektor.json";
import s_olcuye_ozel_cerceve from "../../jenerator/urunler/olcuye-ozel-cerceve.json";
import s_olcuye_ozel_cetvel from "../../jenerator/urunler/olcuye-ozel-cetvel.json";
import s_olcuye_ozel_damga_kase from "../../jenerator/urunler/olcuye-ozel-damga-kase.json";
import s_olcuye_ozel_hortum_adaptoru from "../../jenerator/urunler/olcuye-ozel-hortum-adaptoru.json";
import s_olcuye_ozel_huni from "../../jenerator/urunler/olcuye-ozel-huni.json";
import s_olcuye_ozel_izgara_menfez_kapak from "../../jenerator/urunler/olcuye-ozel-izgara-menfez-kapak.json";
import s_olcuye_ozel_kutu_organizer from "../../jenerator/urunler/olcuye-ozel-kutu-organizer.json";
import s_olcuye_ozel_montaj_braketi from "../../jenerator/urunler/olcuye-ozel-montaj-braketi.json";
import s_olcuye_ozel_oring_conta from "../../jenerator/urunler/olcuye-ozel-oring-conta.json";
import s_olcuye_ozel_pervane_fan_cark from "../../jenerator/urunler/olcuye-ozel-pervane-fan-cark.json";
import s_olcuye_ozel_petek_delikli_panel from "../../jenerator/urunler/olcuye-ozel-petek-delikli-panel.json";
import s_olcuye_ozel_profil_beam from "../../jenerator/urunler/olcuye-ozel-profil-beam.json";
import s_olcuye_ozel_ramp_sim_takoz from "../../jenerator/urunler/olcuye-ozel-ramp-sim-takoz.json";
import s_olcuye_ozel_rulman from "../../jenerator/urunler/olcuye-ozel-rulman.json";
import s_olcuye_ozel_toka from "../../jenerator/urunler/olcuye-ozel-toka.json";
import s_olcuye_ozel_triger_kasnagi from "../../jenerator/urunler/olcuye-ozel-triger-kasnagi.json";
import s_olcuye_ozel_triger_kayisi from "../../jenerator/urunler/olcuye-ozel-triger-kayisi.json";
import s_olcuye_ozel_vida_civata_somun_pul from "../../jenerator/urunler/olcuye-ozel-vida-civata-somun-pul.json";
import s_olcuye_ozel_vidali_kavanoz_tapa from "../../jenerator/urunler/olcuye-ozel-vidali-kavanoz-tapa.json";
import s_olcuye_ozel_yay_dalga_flexure from "../../jenerator/urunler/olcuye-ozel-yay-dalga-flexure.json";
import s_ozel_disli_kramayer_uretimi from "../../jenerator/urunler/ozel-disli-kramayer-uretimi.json";

const HEPSI = [
  s_kisiye_ozel_jeton_cip_madalyon,
  s_olcuye_ozel_baglanti_konektor,
  s_olcuye_ozel_cerceve,
  s_olcuye_ozel_cetvel,
  s_olcuye_ozel_damga_kase,
  s_olcuye_ozel_hortum_adaptoru,
  s_olcuye_ozel_huni,
  s_olcuye_ozel_izgara_menfez_kapak,
  s_olcuye_ozel_kutu_organizer,
  s_olcuye_ozel_montaj_braketi,
  s_olcuye_ozel_oring_conta,
  s_olcuye_ozel_pervane_fan_cark,
  s_olcuye_ozel_petek_delikli_panel,
  s_olcuye_ozel_profil_beam,
  s_olcuye_ozel_ramp_sim_takoz,
  s_olcuye_ozel_rulman,
  s_olcuye_ozel_toka,
  s_olcuye_ozel_triger_kasnagi,
  s_olcuye_ozel_triger_kayisi,
  s_olcuye_ozel_vida_civata_somun_pul,
  s_olcuye_ozel_vidali_kavanoz_tapa,
  s_olcuye_ozel_yay_dalga_flexure,
  s_ozel_disli_kramayer_uretimi,
];

// Anahtar semanin KENDI id'sinden gelir (dosya adindan degil): sema id'si urunler.json'daki
// kebab-id ile eslesmezse zaten sema bulunamaz ve odeme reddedilir. Kapi id'lerin VAR ve
// BENZERSIZ oldugunu uretimden once dogrular (ayni id -> Map sessizce SON kaydi tutardi).
export const SEMALAR = new Map(HEPSI.map((s) => [s.id, s]));

export default SEMALAR;
