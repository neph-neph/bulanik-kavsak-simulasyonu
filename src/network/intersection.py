from collections import deque
from dataclasses import dataclass, field
from statistics import mean
from typing import Callable, Dict, List, Optional

import simpy

from ..controllers import Controller, ControllerState
from ..data.profile import IntersectionProfile
from .vehicle import Vehicle


@dataclass
class IntersectionConfig:
    ad: str
    yonler: List[str]
    profil: IntersectionProfile
    sari_isik_suresi: float = 3.0
    saniyede_gecen_arac: float = 0.55
    yaya_aktif: bool = False
    yaya_min_yesil: float = 8.0
    yaya_gelis_oran: float = 1 / 90.0  # ort 90 sn'de bir yaya gelir


@dataclass
class IntersectionMetrics:
    kavsak_adi: str
    uretilen: int
    gecen: int
    kalan: int
    ortalama_bekleme_toplam: float
    yon_ortalama_bekleme: Dict[str, float]
    maksimum_kuyruk_toplam: int
    ortalama_kuyruk_toplam: float
    yon_max_kuyruk: Dict[str, int]
    gecis_orani: float
    ortalama_yaya_bekleme: float = 0.0
    karsilanan_yaya: int = 0
    bekleyen_yaya: int = 0


class Intersection:

    def __init__(
        self,
        env: simpy.Environment,
        konfig: IntersectionConfig,
        kontrolcu: Controller,
        rastgele,
        sonraki_secici: Optional[Callable[[Vehicle, "Intersection"], Optional["Intersection"]]] = None,
        rota_dogurucu: Optional[Callable[[Vehicle, "Intersection"], None]] = None,
    ):
        self.env = env
        self.konfig = konfig
        self.kontrolcu = kontrolcu
        self.rastgele = rastgele
        self.sonraki_secici = sonraki_secici
        self.rota_dogurucu = rota_dogurucu

        # Her yon icin: kuyruk + sayaclar
        self.kuyruklar: Dict[str, deque] = {yon: deque() for yon in konfig.yonler}
        self.uretilen: Dict[str, int] = {yon: 0 for yon in konfig.yonler}
        self.gecen: Dict[str, int] = {yon: 0 for yon in konfig.yonler}
        self.beklemeler: Dict[str, List[float]] = {yon: [] for yon in konfig.yonler}
        self.en_buyuk_kuyruk: Dict[str, int] = {yon: 0 for yon in konfig.yonler}

        self.aktif_isik: str = konfig.yonler[0]
        self.son_yesil_sureleri: Dict[str, float] = {yon: 0.0 for yon in konfig.yonler}

        # Webster icin: her cevrim sonunda gelen arac sayisini takip et
        self._cevrim_basi_gelis_say: Dict[str, int] = {yon: 0 for yon in konfig.yonler}
        self._cevrim_baslangic_zamani: float = 0.0

        # Yaya
        self.yaya_talepleri: deque = deque()
        self.yaya_karsilanan: List[float] = []
        self.yaya_uretilen: int = 0

        self.gecmis: List[dict] = []

    def _ortalama_bekleme_hesapla(self, yon: str) -> float:
        kuyruk = self.kuyruklar[yon]
        if not kuyruk:
            return 0.0
        toplam = sum(self.env.now - a.geldi_zaman for a in kuyruk)
        return toplam / len(kuyruk)

    def _durum_olustur(self) -> ControllerState:
        return ControllerState(
            aktif_yon=self.aktif_isik,
            yonler=self.konfig.yonler,
            kuyruk_uzunluklari={y: len(self.kuyruklar[y]) for y in self.konfig.yonler},
            ortalama_beklemeler={y: self._ortalama_bekleme_hesapla(y) for y in self.konfig.yonler},
            yaya_beklemesi={"toplam": self._ortalama_yaya_beklemesi()},
            son_yesil_sureleri=dict(self.son_yesil_sureleri),
            simulasyon_zamani=self.env.now,
        )

    def _ortalama_yaya_beklemesi(self) -> float:
        if not self.yaya_talepleri:
            return 0.0
        return sum(self.env.now - t for t in self.yaya_talepleri) / len(self.yaya_talepleri)


    def arac_uretici(self, yon: str, toplam_sure_saniye: float):
        # Poisson sureci: aralar expovariate(lambda) ile rastgele
        sonraki_id = 1
        while self.env.now < toplam_sure_saniye:
            lam = max(self.konfig.profil.lambda_t(yon, self.env.now), 1e-6)
            arada = self.rastgele.expovariate(lam)
            yield self.env.timeout(arada)
            if self.env.now >= toplam_sure_saniye:
                break

            arac = Vehicle(
                id=sonraki_id,
                geldi_zaman=self.env.now,
                yon=yon,
                kavsak_id=self.konfig.ad,
                son_kavsak_giris_zamani=self.env.now,
            )
            if self.rota_dogurucu is not None:
                self.rota_dogurucu(arac, self)
            sonraki_id += 1
            self.araci_ekle(arac, yon)

    def araci_ekle(self, arac: Vehicle, yon: str):
        if yon not in self.kuyruklar:
            return
        arac.son_kavsak_giris_zamani = self.env.now
        self.kuyruklar[yon].append(arac)
        self.uretilen[yon] += 1
        self._cevrim_basi_gelis_say[yon] += 1
        if len(self.kuyruklar[yon]) > self.en_buyuk_kuyruk[yon]:
            self.en_buyuk_kuyruk[yon] = len(self.kuyruklar[yon])

    def yaya_uretici(self, toplam_sure_saniye: float):
        if not self.konfig.yaya_aktif:
            return
        while self.env.now < toplam_sure_saniye:
            arada = self.rastgele.expovariate(self.konfig.yaya_gelis_oran)
            yield self.env.timeout(arada)
            if self.env.now >= toplam_sure_saniye:
                break
            self.yaya_talepleri.append(self.env.now)
            self.yaya_uretilen += 1

    def durum_kaydedici(self, toplam_sure_saniye: float, ornek_aralik: float = 1.0):
        # Her saniye anlik kuyruk ve isik durumunu kaydet
        while self.env.now < toplam_sure_saniye:
            self.gecmis.append(
                {
                    "kavsak": self.konfig.ad,
                    "zaman_saniye": self.env.now,
                    **{f"{y}_kuyruk": len(self.kuyruklar[y]) for y in self.konfig.yonler},
                    "aktif_isik": self.aktif_isik,
                    "yaya_kuyrugu": len(self.yaya_talepleri),
                }
            )
            yield self.env.timeout(ornek_aralik)

    def isik_dongusu(self, toplam_sure_saniye: float):
        siradaki = self.konfig.yonler[0]
        while self.env.now < toplam_sure_saniye:
            self.aktif_isik = siradaki

            self._kontrolcuye_gelis_hizini_bildir()

            durum = self._durum_olustur()
            yesil = max(1.0, float(self.kontrolcu.yesil_sure(durum)))
            self.son_yesil_sureleri[siradaki] = yesil

            yield from self._yesili_isle(siradaki, yesil, toplam_sure_saniye)
            if self.env.now >= toplam_sure_saniye:
                return

            if self.konfig.yaya_aktif and self._yaya_fazi_gerekli():
                yield from self._yaya_fazini_isle(toplam_sure_saniye)

            self.aktif_isik = "sari"
            yield self.env.timeout(self.konfig.sari_isik_suresi)
            if self.env.now >= toplam_sure_saniye:
                return

            idx = self.konfig.yonler.index(siradaki)
            siradaki = self.konfig.yonler[(idx + 1) % len(self.konfig.yonler)]
            self._cevrim_basi_gelis_say = {y: 0 for y in self.konfig.yonler}
            self._cevrim_baslangic_zamani = self.env.now

    def _yesili_isle(self, yon: str, yesil_suresi: float, toplam_sure_saniye: float):
        kalan = yesil_suresi
        gecis_birikim = 0.0
        while kalan > 0 and self.env.now < toplam_sure_saniye:
            dt = min(1.0, kalan)
            yield self.env.timeout(dt)
            kalan -= dt
            gecis_birikim += self.konfig.saniyede_gecen_arac * dt
            gecis_birikim = self._bekleyenleri_gecir(yon, gecis_birikim)

    def _bekleyenleri_gecir(self, yon: str, gecis_birikim: float) -> float:
        # Birikim 1'i gectikce bir arac kavsaktan gecirilir
        while gecis_birikim >= 1.0 and self.kuyruklar[yon]:
            arac = self.kuyruklar[yon].popleft()
            bekleme = self.env.now - arac.son_kavsak_giris_zamani
            self.beklemeler[yon].append(bekleme)
            arac.bekleme_zaman_toplam += bekleme
            self.gecen[yon] += 1
            gecis_birikim -= 1.0
            # Aracin sonraki kavsaga gidip gitmeyecegini sec
            if self.sonraki_secici is not None:
                sonraki = self.sonraki_secici(arac, self)
                if sonraki is not None:
                    arac.rota_indeksi += 1
                    sonraki_yon = arac.sonraki_yon() or yon
                    sonraki.araci_ekle(arac, sonraki_yon)
        return gecis_birikim

    def _yaya_fazi_gerekli(self) -> bool:
        if not self.yaya_talepleri:
            return False
        return (self.env.now - self.yaya_talepleri[0]) > 60.0

    def _yaya_fazini_isle(self, toplam_sure_saniye: float):
        self.aktif_isik = "yaya"
        yield self.env.timeout(self.konfig.yaya_min_yesil)
        while self.yaya_talepleri:
            t = self.yaya_talepleri.popleft()
            self.yaya_karsilanan.append(self.env.now - t)

    def _kontrolcuye_gelis_hizini_bildir(self):
        # Webster vb. icin: gectigimiz cevrimde her yon icin gelis hizini gunder
        if not hasattr(self.kontrolcu, "gelis_hizini_guncelle"):
            return
        gecen_sure = max(self.env.now - self._cevrim_baslangic_zamani, 1.0)
        for yon in self.konfig.yonler:
            hiz = self._cevrim_basi_gelis_say[yon] / gecen_sure
            self.kontrolcu.gelis_hizini_guncelle(yon, hiz)

    def metrikleri_hesapla(self) -> IntersectionMetrics:
        # Simulasyon sonu ozet metrikler
        toplam_bekleme = []
        yon_ortalama = {}
        for yon in self.konfig.yonler:
            yon_ortalama[yon] = mean(self.beklemeler[yon]) if self.beklemeler[yon] else 0.0
            toplam_bekleme.extend(self.beklemeler[yon])

        toplam_uretilen = sum(self.uretilen.values())
        toplam_gecen = sum(self.gecen.values())
        kalan = sum(len(self.kuyruklar[y]) for y in self.konfig.yonler)

        if self.gecmis:
            kuyruk_toplam = [sum(rec[f"{y}_kuyruk"] for y in self.konfig.yonler) for rec in self.gecmis]
            ort_kuyruk = mean(kuyruk_toplam)
            max_kuyruk = max(kuyruk_toplam)
        else:
            ort_kuyruk = 0.0
            max_kuyruk = 0

        yaya_ort = mean(self.yaya_karsilanan) if self.yaya_karsilanan else 0.0

        return IntersectionMetrics(
            kavsak_adi=self.konfig.ad,
            uretilen=toplam_uretilen,
            gecen=toplam_gecen,
            kalan=kalan,
            ortalama_bekleme_toplam=mean(toplam_bekleme) if toplam_bekleme else 0.0,
            yon_ortalama_bekleme=yon_ortalama,
            maksimum_kuyruk_toplam=int(max_kuyruk),
            ortalama_kuyruk_toplam=float(ort_kuyruk),
            yon_max_kuyruk=dict(self.en_buyuk_kuyruk),
            gecis_orani=(toplam_gecen / toplam_uretilen) if toplam_uretilen else 0.0,
            ortalama_yaya_bekleme=float(yaya_ort),
            karsilanan_yaya=len(self.yaya_karsilanan),
            bekleyen_yaya=len(self.yaya_talepleri),
        )
