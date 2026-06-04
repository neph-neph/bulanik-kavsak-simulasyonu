# Ana simulasyon motoru. Topoloji + kontrolcu + profili alir, calistirir, sonuc doner.

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import random

import pandas as pd
import simpy

from .controllers import Controller
from .data.profile import IntersectionProfile
from .network import (
    Intersection,
    IntersectionMetrics,
    Topology,
    build_corridor,
    build_grid_2x2,
    build_single,
)


@dataclass
class SenaryoAyarlari:
    simulasyon_dakika: int = 60
    tohum: int = 42
    yaya_aktif: bool = False
    devam_olasiligi: float = 0.7
    baslangic_saati: int = 7

    def toplam_saniye(self) -> float:
        return self.simulasyon_dakika * 60.0


@dataclass
class SenaryoSonucu:
    topoloji: str
    kontrolcu_adi: str
    metrikler: Dict[str, IntersectionMetrics]
    gecmis: pd.DataFrame
    tohum: int
    toplam_sure_saniye: float

    def ozet_metrikler(self) -> Dict[str, float]:
        # Tum kavsaklar uzerinden agirlikli ortalama metrikler
        toplam_uretilen = sum(m.uretilen for m in self.metrikler.values())
        toplam_gecen = sum(m.gecen for m in self.metrikler.values())
        toplam_kalan = sum(m.kalan for m in self.metrikler.values())
        toplam_yaya = sum(m.karsilanan_yaya for m in self.metrikler.values())

        ort_bekleme = (
            sum(m.ortalama_bekleme_toplam * m.gecen for m in self.metrikler.values()) / toplam_gecen
            if toplam_gecen
            else 0.0
        )
        max_kuyruk_agda = max((m.maksimum_kuyruk_toplam for m in self.metrikler.values()), default=0)
        ort_kuyruk_agda = (
            sum(m.ortalama_kuyruk_toplam for m in self.metrikler.values()) / len(self.metrikler)
            if self.metrikler
            else 0.0
        )
        gecis_orani = (toplam_gecen / toplam_uretilen) if toplam_uretilen else 0.0
        ort_yaya = (
            sum(m.ortalama_yaya_bekleme * m.karsilanan_yaya for m in self.metrikler.values()) / toplam_yaya
            if toplam_yaya
            else 0.0
        )
        return {
            "uretilen": toplam_uretilen,
            "gecen": toplam_gecen,
            "kalan": toplam_kalan,
            "ortalama_bekleme_sn": round(ort_bekleme, 2),
            "max_kuyruk": int(max_kuyruk_agda),
            "ortalama_kuyruk": round(ort_kuyruk_agda, 2),
            "gecis_orani": round(gecis_orani, 3),
            "ortalama_yaya_bekleme_sn": round(ort_yaya, 2),
        }


def _topoloji_olustur(
    topoloji: str,
    env: simpy.Environment,
    profiller,
    kontrolcu_fab: Callable[[], Controller],
    rastgele,
    ayarlar: SenaryoAyarlari,
) -> Topology:
    topoloji = topoloji.lower()
    if topoloji == "single":
        if isinstance(profiller, list):
            profil = profiller[0]
        elif isinstance(profiller, dict):
            profil = next(iter(profiller.values()))
        else:
            profil = profiller
        return build_single(env, profil, kontrolcu_fab, rastgele, yaya_aktif=ayarlar.yaya_aktif)
    if topoloji == "corridor":
        return build_corridor(
            env,
            list(profiller),
            kontrolcu_fab,
            rastgele,
            yaya_aktif=ayarlar.yaya_aktif,
            devam_olasiligi=ayarlar.devam_olasiligi,
        )
    if topoloji == "grid_2x2":
        return build_grid_2x2(
            env,
            profiller,
            kontrolcu_fab,
            rastgele,
            yaya_aktif=ayarlar.yaya_aktif,
            devam_olasiligi=ayarlar.devam_olasiligi,
        )
    raise ValueError(f"Bilinmeyen topoloji: {topoloji}")


def senaryo_calistir(
    topoloji: str,
    kontrolcu_fab: Callable[[], Controller],
    profiller,
    ayarlar: Optional[SenaryoAyarlari] = None,
) -> SenaryoSonucu:
    if ayarlar is None:
        ayarlar = SenaryoAyarlari()

    env = simpy.Environment()
    rastgele = random.Random(ayarlar.tohum)
    top = _topoloji_olustur(topoloji, env, profiller, kontrolcu_fab, rastgele, ayarlar)
    top.tum_islemleri_baslat(ayarlar.toplam_saniye())
    env.run(until=ayarlar.toplam_saniye())

    metrikler = {ad: k.metrikleri_hesapla() for ad, k in top.kavsaklar.items()}
    gecmis_kayitlari = []
    for k in top.kavsaklar.values():
        gecmis_kayitlari.extend(k.gecmis)
    gecmis_df = pd.DataFrame(gecmis_kayitlari)

    # Kontrolcü adı (ilk kavşaktan)
    ilk_kavsak = next(iter(top.kavsaklar.values()))
    kontrolcu_adi = ilk_kavsak.kontrolcu.adi()

    return SenaryoSonucu(
        topoloji=topoloji,
        kontrolcu_adi=kontrolcu_adi,
        metrikler=metrikler,
        gecmis=gecmis_df,
        tohum=ayarlar.tohum,
        toplam_sure_saniye=ayarlar.toplam_saniye(),
    )


def coklu_kontrolcu_karsilastir(
    topoloji: str,
    kontrolcu_fabrikalari: Dict[str, Callable[[], Controller]],
    profiller,
    ayarlar: Optional[SenaryoAyarlari] = None,
) -> Dict[str, SenaryoSonucu]:
    # Bir senaryo icin tum kontrolculeri calistir, sonuclari dict olarak don
    sonuclar: Dict[str, SenaryoSonucu] = {}
    for ad, fab in kontrolcu_fabrikalari.items():
        sonuclar[ad] = senaryo_calistir(topoloji, fab, profiller, ayarlar)
    return sonuclar
