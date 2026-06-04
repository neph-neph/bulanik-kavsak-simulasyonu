from dataclasses import dataclass, field
from math import sqrt
from typing import Callable, Dict, List, Optional

import pandas as pd

from ..controllers import Controller
from ..engine import SenaryoAyarlari, senaryo_calistir


# t kritik degerleri (iki yonlu, alpha=0.05). n>=100 icin 1.96 yaklasimi yeterli.
T_KRITIK = {
    5: 2.776, 10: 2.262, 15: 2.145, 20: 2.093, 25: 2.064, 30: 2.045,
    40: 2.021, 50: 2.009, 100: 1.984,
}


def _t_kritik(n: int, alpha: float = 0.05) -> float:
    if n >= 100:
        return 1.984
    for boyut in sorted(T_KRITIK):
        if n <= boyut:
            return T_KRITIK[boyut]
    return 1.984


@dataclass
class KontrolcuOzet:
    kontrolcu_adi: str
    n_tohum: int
    metrik_ortalama: Dict[str, float]
    metrik_std: Dict[str, float]
    metrik_guven_araligi: Dict[str, tuple]
    ham_calistirmalar: pd.DataFrame = field(default_factory=pd.DataFrame)


def coklu_tohum_calistir(
    topoloji: str,
    kontrolcu_fab: Callable[[], Controller],
    profiller,
    tohumlar: List[int],
    temel_ayarlar: Optional[SenaryoAyarlari] = None,
) -> KontrolcuOzet:
    # Ayni kontrolcuyu farkli tohumlarla calistirip ortalama+CI dondur
    temel = temel_ayarlar or SenaryoAyarlari()
    satirlar = []
    kontrolcu_adi = "?"
    for tohum in tohumlar:
        ayar = SenaryoAyarlari(
            simulasyon_dakika=temel.simulasyon_dakika,
            tohum=tohum,
            yaya_aktif=temel.yaya_aktif,
            devam_olasiligi=temel.devam_olasiligi,
            baslangic_saati=temel.baslangic_saati,
        )
        sonuc = senaryo_calistir(topoloji, kontrolcu_fab, profiller, ayar)
        kontrolcu_adi = sonuc.kontrolcu_adi
        ozet = sonuc.ozet_metrikler()
        ozet["tohum"] = tohum
        satirlar.append(ozet)

    df = pd.DataFrame(satirlar)
    metrik_sutunlari = [c for c in df.columns if c != "tohum"]
    ortalama = {c: float(df[c].mean()) for c in metrik_sutunlari}
    std = {c: float(df[c].std(ddof=1)) if len(df) > 1 else 0.0 for c in metrik_sutunlari}

    n = len(df)
    t_kr = _t_kritik(n)
    guven = {}
    for c in metrik_sutunlari:
        if n <= 1:
            guven[c] = (ortalama[c], ortalama[c])
        else:
            sem = std[c] / sqrt(n)
            yari_genislik = t_kr * sem
            guven[c] = (ortalama[c] - yari_genislik, ortalama[c] + yari_genislik)

    return KontrolcuOzet(
        kontrolcu_adi=kontrolcu_adi,
        n_tohum=n,
        metrik_ortalama=ortalama,
        metrik_std=std,
        metrik_guven_araligi=guven,
        ham_calistirmalar=df,
    )


def welch_t_testi(orneklem_1: List[float], orneklem_2: List[float]) -> Dict[str, float]:
    # Welch t-testi: iki ornekleme varyanslari farkli olabilir (esit varyans varsayilmaz)
    n1, n2 = len(orneklem_1), len(orneklem_2)
    if n1 < 2 or n2 < 2:
        return {"t": 0.0, "p_yaklasik": 1.0, "anlamli_alpha_005": False}

    m1 = sum(orneklem_1) / n1
    m2 = sum(orneklem_2) / n2
    v1 = sum((x - m1) ** 2 for x in orneklem_1) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in orneklem_2) / (n2 - 1)

    if v1 == 0 and v2 == 0:
        return {"t": 0.0, "p_yaklasik": 1.0, "anlamli_alpha_005": False}

    se = sqrt(v1 / n1 + v2 / n2)
    t = (m1 - m2) / se if se > 0 else 0.0

    # Welch-Satterthwaite serbestlik derecesi (df)
    pay = (v1 / n1 + v2 / n2) ** 2
    payda = (v1 ** 2) / (n1 ** 2 * (n1 - 1)) + (v2 ** 2) / (n2 ** 2 * (n2 - 1))
    df = pay / payda if payda > 0 else max(n1, n2) - 1
    t_kr = _t_kritik(int(df))

    return {
        "t": float(t),
        "df": float(df),
        "anlamli_alpha_005": abs(t) > t_kr,
        "kritik_t": t_kr,
    }


def kontrolcu_karsilastirmasi(
    topoloji: str,
    kontrolcu_fabrikalari: Dict[str, Callable[[], Controller]],
    profiller,
    tohumlar: List[int],
    temel_ayarlar: Optional[SenaryoAyarlari] = None,
    referans_kontrolcu: str = "Sabit Süreli",
    karsilastirma_metrigi: str = "ortalama_bekleme_sn",
) -> Dict:
    # Tum kontrolculeri N tohumla calistir, ozet tablo + t-test dondur
    ham_sonuclar: Dict[str, KontrolcuOzet] = {}
    for ad, fab in kontrolcu_fabrikalari.items():
        ham_sonuclar[ad] = coklu_tohum_calistir(topoloji, fab, profiller, tohumlar, temel_ayarlar)

    metrik_sutunlari = list(next(iter(ham_sonuclar.values())).metrik_ortalama.keys())

    # "ort +/- yari_genislik" formatinda gorsel ozet
    satirlar = []
    for ad, ozet in ham_sonuclar.items():
        satir = {"kontrolcu": ad, "n": ozet.n_tohum}
        for c in metrik_sutunlari:
            ort = ozet.metrik_ortalama[c]
            ci_alt, ci_ust = ozet.metrik_guven_araligi[c]
            yari = (ci_ust - ci_alt) / 2
            satir[c] = f"{ort:.2f} ± {yari:.2f}"
        satirlar.append(satir)
    ozet_df = pd.DataFrame(satirlar)

    # t-test: referans kontrolcu vs digerleri
    t_sonuclari = {}
    if referans_kontrolcu in ham_sonuclar:
        ref_orneklem = ham_sonuclar[referans_kontrolcu].ham_calistirmalar[karsilastirma_metrigi].tolist()
        for ad, ozet in ham_sonuclar.items():
            if ad == referans_kontrolcu:
                continue
            ote_orneklem = ozet.ham_calistirmalar[karsilastirma_metrigi].tolist()
            t_sonuclari[ad] = welch_t_testi(ref_orneklem, ote_orneklem)

    return {
        "ozet_tablosu": ozet_df,
        "t_test_sonuclari": t_sonuclari,
        "ham_sonuclar": ham_sonuclar,
        "karsilastirma_metrigi": karsilastirma_metrigi,
        "referans_kontrolcu": referans_kontrolcu,
    }
