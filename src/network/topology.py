from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import simpy

from ..controllers import Controller
from ..data.profile import IntersectionProfile
from .intersection import Intersection, IntersectionConfig
from .vehicle import Vehicle


@dataclass
class Topology:
    ad: str
    kavsaklar: Dict[str, Intersection]
    cevre_giris_yonleri: Dict[str, List[str]] = field(default_factory=dict)

    def tum_islemleri_baslat(self, toplam_sure_saniye: float):
        env = next(iter(self.kavsaklar.values())).env
        for kavsak in self.kavsaklar.values():
            # Sadece dışarıdan trafik alan yönler için üretici ekle
            cevre_yonler = self.cevre_giris_yonleri.get(kavsak.konfig.ad, kavsak.konfig.yonler)
            for yon in cevre_yonler:
                env.process(kavsak.arac_uretici(yon, toplam_sure_saniye))
            env.process(kavsak.durum_kaydedici(toplam_sure_saniye))
            env.process(kavsak.isik_dongusu(toplam_sure_saniye))
            if kavsak.konfig.yaya_aktif:
                env.process(kavsak.yaya_uretici(toplam_sure_saniye))


def _intersection_olustur(
    env: simpy.Environment,
    ad: str,
    profil: IntersectionProfile,
    kontrolcu_fab: Callable[[], Controller],
    rastgele,
    sonraki_secici: Optional[Callable[[Vehicle, Intersection], Optional[Intersection]]] = None,
    yaya_aktif: bool = False,
) -> Intersection:
    konfig = IntersectionConfig(
        ad=ad,
        yonler=profil.yonler(),
        profil=profil,
        yaya_aktif=yaya_aktif,
    )
    return Intersection(
        env=env,
        konfig=konfig,
        kontrolcu=kontrolcu_fab(),
        rastgele=rastgele,
        sonraki_secici=sonraki_secici,
    )


def build_single(
    env: simpy.Environment,
    profil: IntersectionProfile,
    kontrolcu_fab: Callable[[], Controller],
    rastgele,
    yaya_aktif: bool = False,
) -> Topology:
    kavsak = _intersection_olustur(env, "K1", profil, kontrolcu_fab, rastgele, yaya_aktif=yaya_aktif)
    return Topology(ad="single", kavsaklar={"K1": kavsak})


def build_corridor(
    env: simpy.Environment,
    profiller: List[IntersectionProfile],
    kontrolcu_fab: Callable[[], Controller],
    rastgele,
    yaya_aktif: bool = False,
    devam_olasiligi: float = 0.7,
) -> Topology:
    # 4'lu koridor: K1 -> K2 -> K3 -> K4.
    # devam_olasiligi ile sonraki kavsaga gecer, yoksa agdan cikar.
    if len(profiller) < 2:
        raise ValueError("Koridor için en az 2 profil gerekli")

    kavsaklar: Dict[str, Intersection] = {}
    for i, profil in enumerate(profiller):
        ad = f"K{i + 1}"
        kavsaklar[ad] = _intersection_olustur(
            env, ad, profil, kontrolcu_fab, rastgele, yaya_aktif=yaya_aktif
        )

    isim_listesi = list(kavsaklar.keys())

    def sonraki_secici(arac: Vehicle, su_an: Intersection) -> Optional[Intersection]:
        idx = isim_listesi.index(su_an.konfig.ad)
        if idx + 1 >= len(isim_listesi):
            return None
        if rastgele.random() > devam_olasiligi:
            return None
        return kavsaklar[isim_listesi[idx + 1]]

    for kavsak in kavsaklar.values():
        kavsak.sonraki_secici = sonraki_secici

    cevre = {ad: ([] if i > 0 else kavsaklar[ad].konfig.yonler) for i, ad in enumerate(isim_listesi)}
    #tüm kavşakların dogu_bati yönü dışarıdan beslenir, kuzey_guney akış zinciri
    for i, ad in enumerate(isim_listesi):
        if i == 0:
            cevre[ad] = kavsaklar[ad].konfig.yonler  # K1: hepsi dışarıdan
        else:
            cevre[ad] = ["dogu_bati"]  # alttaki kavşaklarda sadece DB dışarıdan

    return Topology(ad="corridor", kavsaklar=kavsaklar, cevre_giris_yonleri=cevre)


def build_grid_2x2(
    env: simpy.Environment,
    profiller: Dict[str, IntersectionProfile],
    kontrolcu_fab: Callable[[], Controller],
    rastgele,
    yaya_aktif: bool = False,
    devam_olasiligi: float = 0.6,
) -> Topology:
    # 2x2 grid:  K11-K12
    #            K21-K22
    # Yatay komsular dogu_bati, dikey komsular kuzey_guney uzerinden bagli.
    gerekli = {"K11", "K12", "K21", "K22"}
    if set(profiller.keys()) != gerekli:
        raise ValueError(f"2x2 grid için profil anahtarları {gerekli} olmalı, verilen: {set(profiller.keys())}")

    kavsaklar: Dict[str, Intersection] = {}
    for ad, profil in profiller.items():
        kavsaklar[ad] = _intersection_olustur(
            env, ad, profil, kontrolcu_fab, rastgele, yaya_aktif=yaya_aktif
        )

    # Komşuluk haritası: (kavşak, çıkış_yön) -> (sonraki_kavşak, giriş_yön)
    komsuluk = {
        ("K11", "dogu_bati"): ("K12", "dogu_bati"),
        ("K11", "kuzey_guney"): ("K21", "kuzey_guney"),
        ("K12", "dogu_bati"): (None, None),  # ağdan çıkış
        ("K12", "kuzey_guney"): ("K22", "kuzey_guney"),
        ("K21", "dogu_bati"): ("K22", "dogu_bati"),
        ("K21", "kuzey_guney"): (None, None),
        ("K22", "dogu_bati"): (None, None),
        ("K22", "kuzey_guney"): (None, None),
    }

    def sonraki_secici(arac: Vehicle, su_an: Intersection) -> Optional[Intersection]:
        anahtar = (su_an.konfig.ad, arac.yon)
        sonraki_ad, sonraki_yon = komsuluk.get(anahtar, (None, None))
        if sonraki_ad is None:
            return None
        if rastgele.random() > devam_olasiligi:
            return None
        arac.yon = sonraki_yon
        return kavsaklar[sonraki_ad]

    for kavsak in kavsaklar.values():
        kavsak.sonraki_secici = sonraki_secici

    # Dışarıdan giriş: tüm kavşaklarda hem KG hem DB dışarıdan trafik alır
    cevre = {ad: kavsaklar[ad].konfig.yonler for ad in kavsaklar}
    return Topology(ad="grid_2x2", kavsaklar=kavsaklar, cevre_giris_yonleri=cevre)
