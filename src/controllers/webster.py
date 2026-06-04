from typing import Dict

from .base import Controller, ControllerState

# Tek seritli kentsel kavsak icin tipik doygunluk akisi (~1800 arac/saat)
VARSAYILAN_DOYGUNLUK = 0.5


class WebsterController(Controller):
    # Webster 1958 formulu: C* = (1.5*L + 5) / (1 - Y)
    # L: kayip sure (sari isiklar), Y: yon doygunluk oranlari toplami
    isim = "Webster"

    def __init__(
        self,
        kayip_suresi: float = 4.0,
        doygunluk_akisi: float = VARSAYILAN_DOYGUNLUK,
        min_yesil: float = 8.0,
        max_yesil: float = 60.0,
        gozlem_penceresi: float = 60.0,
    ):
        self.kayip_suresi = kayip_suresi
        self.doygunluk = doygunluk_akisi
        self.min_yesil = min_yesil
        self.max_yesil = max_yesil
        self.gozlem_penceresi = gozlem_penceresi
        # Her yonun anlik gelis hizi tahmini (simulasyon her cevrim bunu gunceller)
        self._son_gelis_hizlari: Dict[str, float] = {}

    def gelis_hizini_guncelle(self, yon: str, gelis_hizi_arac_sn: float):
        self._son_gelis_hizlari[yon] = max(gelis_hizi_arac_sn, 1e-6)

    def yesil_sure(self, durum: ControllerState) -> float:
        yonler = durum.yonler

        if not self._son_gelis_hizlari:
            for yon in yonler:
                self._son_gelis_hizlari[yon] = max(
                    durum.kuyruk_uzunluklari.get(yon, 0) / self.gozlem_penceresi, 0.05
                )

        y_degerleri = {
            yon: self._son_gelis_hizlari.get(yon, 0.05) / self.doygunluk
            for yon in yonler
        }
        Y = min(sum(y_degerleri.values()), 0.95)
        if Y <= 0:
            return self.min_yesil

        L = self.kayip_suresi * len(yonler)
        C_opt = (1.5 * L + 5.0) / (1.0 - Y)
        toplam_yesil = max(C_opt - L, len(yonler) * self.min_yesil)

        aktif = durum.aktif_yon
        toplam_y = sum(y_degerleri.values())
        pay = (y_degerleri.get(aktif, 0.0) / toplam_y) if toplam_y > 0 else 1.0 / len(yonler)

        yesil = pay * toplam_yesil
        if yesil < self.min_yesil:
            yesil = self.min_yesil
        if yesil > self.max_yesil:
            yesil = self.max_yesil
        return float(yesil)
