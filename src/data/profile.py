from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class TrafficProfile:
    saatlik_arac_sayisi: Sequence[float]
    olcekleme: float = 1.0
    etiket: str = ""

    def __post_init__(self):
        if len(self.saatlik_arac_sayisi) != 24:
            raise ValueError(f"24 deger gerekli, {len(self.saatlik_arac_sayisi)} verildi")

    def lambda_t(self, simulasyon_saniyesi: float, baslangic_saati: int = 7) -> float:
        toplam_saniye = (baslangic_saati * 3600 + simulasyon_saniyesi) % (24 * 3600)
        saat_indeksi = toplam_saniye / 3600.0
        alt_saat = int(saat_indeksi) % 24
        ust_saat = (alt_saat + 1) % 24
        oran = saat_indeksi - int(saat_indeksi)

        alt = self.saatlik_arac_sayisi[alt_saat]
        ust = self.saatlik_arac_sayisi[ust_saat]
        arac_saat = (1 - oran) * alt + oran * ust
        return (arac_saat * self.olcekleme) / 3600.0


@dataclass
class IntersectionProfile:
    # Bir kavsagin tum yonleri icin profil
    yon_profilleri: Dict[str, TrafficProfile]
    ad: str = "kavsak"
    baslangic_saati: int = 7

    def lambda_t(self, yon: str, simulasyon_saniyesi: float) -> float:
        return self.yon_profilleri[yon].lambda_t(simulasyon_saniyesi, baslangic_saati=self.baslangic_saati)

    def yonler(self) -> List[str]:
        return list(self.yon_profilleri.keys())
