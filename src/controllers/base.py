from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ControllerState:
    # Kontrolcuye verilen anlik kavsak durumu
    aktif_yon: str
    yonler: List[str]
    kuyruk_uzunluklari: Dict[str, int]
    ortalama_beklemeler: Dict[str, float]
    yaya_beklemesi: Dict[str, float] = field(default_factory=dict)
    son_yesil_sureleri: Dict[str, float] = field(default_factory=dict)
    simulasyon_zamani: float = 0.0


class Controller:
    # Tum kontrolculerin atasi. yesil_sure() metodunu cocuk siniflar yazar.
    isim: str = "base"

    def yesil_sure(self, durum: ControllerState) -> float:
        raise NotImplementedError

    def adi(self) -> str:
        return self.isim
