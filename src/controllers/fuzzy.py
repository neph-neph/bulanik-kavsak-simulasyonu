from .base import Controller, ControllerState


def ucgen_uyelik(deger, sol, orta, sag):
    if deger <= sol or deger >= sag:
        return 0.0
    if deger == orta:
        return 1.0
    if deger < orta:
        return (deger - sol) / (orta - sol)
    return (sag - deger) / (sag - orta)


# Yamuk uyelik fonksiyonu: duz bir tepe + iki yan rampa
def yamuk_uyelik(deger, sol, sol_tepe, sag_tepe, sag):
    if deger < sol or deger > sag:
        return 0.0
    if sol_tepe <= deger <= sag_tepe:
        return 1.0
    if deger < sol_tepe:
        if sol_tepe == sol:
            return 1.0
        return (deger - sol) / (sol_tepe - sol)
    if sag_tepe == sag:
        return 1.0
    return (sag - deger) / (sag - sag_tepe)


def yesil_sure_hesapla(
    kuyruk_uzunlugu,
    ort_bekleme,
    karsi_kuyruk=0,
    min_yesil=12,
    orta_yesil=24,
    max_yesil=40,
):


    kuyruk_az = yamuk_uyelik(kuyruk_uzunlugu, 0, 0, 4, 10)
    kuyruk_orta = ucgen_uyelik(kuyruk_uzunlugu, 6, 14, 24)
    kuyruk_fazla = yamuk_uyelik(kuyruk_uzunlugu, 18, 26, 40, 40)

    bekleme_az = yamuk_uyelik(ort_bekleme, 0, 0, 6, 15)
    bekleme_orta = ucgen_uyelik(ort_bekleme, 10, 22, 38)
    bekleme_fazla = yamuk_uyelik(ort_bekleme, 30, 45, 90, 90)

    karsi_az = yamuk_uyelik(karsi_kuyruk, 0, 0, 4, 10)
    karsi_orta = ucgen_uyelik(karsi_kuyruk, 6, 14, 24)
    karsi_fazla = yamuk_uyelik(karsi_kuyruk, 18, 26, 40, 40)

    kisa = max(
        min(kuyruk_az, bekleme_az),
        min(kuyruk_az, bekleme_orta),
        min(kuyruk_orta, bekleme_az),
        karsi_fazla,
    )

    orta = max(
        min(kuyruk_orta, bekleme_orta),
        min(kuyruk_fazla, bekleme_az),
        min(kuyruk_az, bekleme_fazla),
        min(kuyruk_fazla, karsi_orta),
        min(kuyruk_orta, karsi_orta),
    )

    uzun = max(
        min(kuyruk_fazla, karsi_az),
        min(bekleme_fazla, karsi_az),
        min(kuyruk_orta, bekleme_fazla),
        min(kuyruk_fazla, bekleme_orta),
    )

    # Durulastirma
    toplam_agirlik = kisa + orta + uzun
    if toplam_agirlik == 0:
        return float(min_yesil)

    yesil = (kisa * min_yesil + orta * orta_yesil + uzun * max_yesil) / toplam_agirlik

    if yesil < min_yesil:
        yesil = min_yesil
    if yesil > max_yesil:
        yesil = max_yesil
    return float(yesil)


class FuzzyController(Controller):
    isim = "Bulanık Mantık"

    def __init__(self, min_yesil=12, orta_yesil=24, max_yesil=40, karsi_yon_kullan=True):
        self.min_yesil = min_yesil
        self.orta_yesil = orta_yesil
        self.max_yesil = max_yesil
        self.karsi_yon_kullan = karsi_yon_kullan

    def _karsi_yon(self, durum: ControllerState) -> str:
        for yon in durum.yonler:
            if yon != durum.aktif_yon:
                return yon
        return durum.aktif_yon

    def yesil_sure(self, durum: ControllerState) -> float:
        yon = durum.aktif_yon
        kuyruk = durum.kuyruk_uzunluklari.get(yon, 0)
        bekleme = durum.ortalama_beklemeler.get(yon, 0.0)

        karsi_kuyruk = 0
        if self.karsi_yon_kullan:
            karsi = self._karsi_yon(durum)
            karsi_kuyruk = durum.kuyruk_uzunluklari.get(karsi, 0)

        return yesil_sure_hesapla(
            kuyruk,
            bekleme,
            karsi_kuyruk=karsi_kuyruk,
            min_yesil=self.min_yesil,
            orta_yesil=self.orta_yesil,
            max_yesil=self.max_yesil,
        )
