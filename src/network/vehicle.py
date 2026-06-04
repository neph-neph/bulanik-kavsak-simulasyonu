from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Vehicle:
    # Bir arac. Yaratildigi andan ayrildiga kadar izlenir.
    id: int
    geldi_zaman: float
    yon: str
    kavsak_id: str
    rota: List[str] = field(default_factory=list)
    rota_indeksi: int = 0
    yon_zinciri: List[str] = field(default_factory=list)
    bekleme_zaman_toplam: float = 0.0
    son_kavsak_giris_zamani: float = 0.0

    def sonraki_kavsak(self) -> Optional[str]:
        if self.rota_indeksi + 1 >= len(self.rota):
            return None
        return self.rota[self.rota_indeksi + 1]

    def sonraki_yon(self) -> Optional[str]:
        if self.rota_indeksi + 1 >= len(self.yon_zinciri):
            return None
        return self.yon_zinciri[self.rota_indeksi + 1]
