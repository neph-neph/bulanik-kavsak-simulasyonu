from .base import Controller, ControllerState


class FixedController(Controller):
    isim = "Sabit Süreli"

    def __init__(self, yesil_suresi: float = 20.0):
        self.sabit_yesil = float(yesil_suresi)

    def yesil_sure(self, durum: ControllerState) -> float:
        return self.sabit_yesil
