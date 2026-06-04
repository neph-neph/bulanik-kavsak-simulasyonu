from .base import Controller, ControllerState


class ActuatedController(Controller):
    # Gap-out mantigi: kuyruk varsa yesili uzat, bosalinca sonraki yone gec.
    isim = "Aktüe (Gap-out)"

    def __init__(
        self,
        min_yesil: float = 10.0,
        max_yesil: float = 50.0,
        uzatma_birimi: float = 4.0,
        gap_esigi: float = 2.5,
    ):
        self.min_yesil = min_yesil
        self.max_yesil = max_yesil
        self.uzatma_birimi = uzatma_birimi
        self.gap_esigi = gap_esigi

    def yesil_sure(self, durum: ControllerState) -> float:
        yon = durum.aktif_yon
        kuyruk = durum.kuyruk_uzunluklari.get(yon, 0)

        # Bos kuyruk -> minimum yesil
        if kuyruk <= 1:
            return self.min_yesil

        tahmini = self.min_yesil + kuyruk * self.uzatma_birimi
        return float(min(tahmini, self.max_yesil))
