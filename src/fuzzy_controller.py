def ucgen_uyelik(deger, sol, orta, sag):
    if deger <= sol or deger >= sag:
        return 0.0
    if deger == orta:
        return 1.0
    if deger < orta:
        return (deger - sol) / (orta - sol)
    return (sag - deger) / (sag - orta)


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


def yesil_sure_hesapla(kuyruk_uzunlugu, ort_bekleme, min_yesil=12, orta_yesil=24, max_yesil=40):
    kuyruk_az = yamuk_uyelik(kuyruk_uzunlugu, 0, 0, 4, 10)
    kuyruk_orta = ucgen_uyelik(kuyruk_uzunlugu, 6, 14, 24)
    kuyruk_fazla = yamuk_uyelik(kuyruk_uzunlugu, 18, 26, 40, 40)

    bekleme_az = yamuk_uyelik(ort_bekleme, 0, 0, 6, 15)
    bekleme_orta = ucgen_uyelik(ort_bekleme, 10, 22, 38)
    bekleme_fazla = yamuk_uyelik(ort_bekleme, 30, 45, 90, 90)

    kisa_yesil = max(
        min(kuyruk_az, bekleme_az),
        min(kuyruk_az, bekleme_orta),
        min(kuyruk_orta, bekleme_az),
    )

    orta_yesil_gucu = max(
        min(kuyruk_orta, bekleme_orta),
        min(kuyruk_fazla, bekleme_az),
        min(kuyruk_az, bekleme_fazla),
    )

    uzun_yesil = max(
        kuyruk_fazla,
        bekleme_fazla,
        min(kuyruk_orta, bekleme_fazla),
        min(kuyruk_fazla, bekleme_orta),
    )

    toplam_agirlik = kisa_yesil + orta_yesil_gucu + uzun_yesil
    if toplam_agirlik == 0:
        return min_yesil

    yesil_sure = (
        kisa_yesil * min_yesil
        + orta_yesil_gucu * orta_yesil
        + uzun_yesil * max_yesil
    ) / toplam_agirlik

    if yesil_sure < min_yesil:
        yesil_sure = min_yesil
    if yesil_sure > max_yesil:
        yesil_sure = max_yesil

    return int(round(yesil_sure))
