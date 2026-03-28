from collections import deque
import random
from statistics import mean

import pandas as pd
import simpy

from fuzzy_controller import yesil_sure_hesapla


TRAFIK_EVRELERI = [
    {"bitis_dakikasi": 20, "kuzey_guney": 18, "dogu_bati": 9},
    {"bitis_dakikasi": 40, "kuzey_guney": 12, "dogu_bati": 12},
    {"bitis_dakikasi": 60, "kuzey_guney": 8, "dogu_bati": 16},
]


class SimulasyonAyarlari:
    def __init__(
        self,
        simulasyon_suresi_dakika=60,
        sabit_yesil_suresi=20,
        sari_isik_suresi=3,
        saniyede_gecen_arac=0.55,
        tohum=42,
    ):
        self.simulasyon_suresi_dakika = simulasyon_suresi_dakika
        self.sabit_yesil_suresi = sabit_yesil_suresi
        self.sari_isik_suresi = sari_isik_suresi
        self.saniyede_gecen_arac = saniyede_gecen_arac
        self.tohum = tohum

    def toplam_sure_saniye(self):
        return self.simulasyon_suresi_dakika * 60


class TrafikSimulasyonu:
    def __init__(self, kontrol_tipi, ayarlar=None, trafik_evreleri=None):
        self.kontrol_tipi = kontrol_tipi
        self.ayarlar = ayarlar if ayarlar is not None else SimulasyonAyarlari()
        self.trafik_evreleri = trafik_evreleri if trafik_evreleri is not None else TRAFIK_EVRELERI

        self.env = simpy.Environment()
        self.rastgele = random.Random(self.ayarlar.tohum)

        self.kuyruklar = {"kuzey_guney": deque(), "dogu_bati": deque()}
        self.uretilen_arac_sayisi = {"kuzey_guney": 0, "dogu_bati": 0}
        self.gecen_arac_sayisi = {"kuzey_guney": 0, "dogu_bati": 0}
        self.bekleme_sureleri = {"kuzey_guney": [], "dogu_bati": []}
        self.en_buyuk_kuyruk = {"kuzey_guney": 0, "dogu_bati": 0}

        self.gecmis_kayitlari = []
        self.aktif_isik = "kuzey_guney"

    def gelis_hizi_bul(self, yon):
        simdiki_dakika = self.env.now / 60
        for evre in self.trafik_evreleri:
            if simdiki_dakika < evre["bitis_dakikasi"]:
                return evre[yon]
        return self.trafik_evreleri[-1][yon]

    def ortalama_bekleme_bul(self, yon):
        kuyruk = self.kuyruklar[yon]
        if not kuyruk:
            return 0.0

        toplam_bekleme = 0.0
        for gelis_zamani in kuyruk:
            toplam_bekleme += self.env.now - gelis_zamani

        return toplam_bekleme / len(kuyruk)

    def yesil_sure_belirle(self, yon):
        if self.kontrol_tipi == "sabit":
            return self.ayarlar.sabit_yesil_suresi

        return yesil_sure_hesapla(
            len(self.kuyruklar[yon]),
            self.ortalama_bekleme_bul(yon),
        )

    def arac_uret(self, yon):
        while self.env.now < self.ayarlar.toplam_sure_saniye():
            dakikadaki_arac = self.gelis_hizi_bul(yon)

            if dakikadaki_arac <= 0:
                yield self.env.timeout(1)
                continue

            sure = self.rastgele.expovariate(dakikadaki_arac / 60)
            yield self.env.timeout(sure)

            if self.env.now >= self.ayarlar.toplam_sure_saniye():
                break

            self.kuyruklar[yon].append(self.env.now)
            self.uretilen_arac_sayisi[yon] += 1

            mevcut_uzunluk = len(self.kuyruklar[yon])
            if mevcut_uzunluk > self.en_buyuk_kuyruk[yon]:
                self.en_buyuk_kuyruk[yon] = mevcut_uzunluk

    def durum_kaydet(self):
        while self.env.now < self.ayarlar.toplam_sure_saniye():
            self.gecmis_kayitlari.append(
                {
                    "zaman_saniye": self.env.now,
                    "kuzey_guney_kuyruk": len(self.kuyruklar["kuzey_guney"]),
                    "dogu_bati_kuyruk": len(self.kuyruklar["dogu_bati"]),
                    "aktif_isik": self.aktif_isik,
                }
            )

            if len(self.kuyruklar["kuzey_guney"]) > self.en_buyuk_kuyruk["kuzey_guney"]:
                self.en_buyuk_kuyruk["kuzey_guney"] = len(self.kuyruklar["kuzey_guney"])
            if len(self.kuyruklar["dogu_bati"]) > self.en_buyuk_kuyruk["dogu_bati"]:
                self.en_buyuk_kuyruk["dogu_bati"] = len(self.kuyruklar["dogu_bati"])

            yield self.env.timeout(1)

    def bekleyen_araclari_gecir(self, yon, gecis_hakki):
        while gecis_hakki >= 1 and self.kuyruklar[yon]:
            gelis_zamani = self.kuyruklar[yon].popleft()
            self.bekleme_sureleri[yon].append(self.env.now - gelis_zamani)
            self.gecen_arac_sayisi[yon] += 1
            gecis_hakki -= 1

        return gecis_hakki

    def isik_dongusu(self):
        siradaki_yon = "kuzey_guney"

        while self.env.now < self.ayarlar.toplam_sure_saniye():
            yesil = self.yesil_sure_belirle(siradaki_yon)
            self.aktif_isik = siradaki_yon
            gecis_hakki = 0.0

            for i in range(yesil):
                if self.env.now >= self.ayarlar.toplam_sure_saniye():
                    return

                gecis_hakki += self.ayarlar.saniyede_gecen_arac
                gecis_hakki = self.bekleyen_araclari_gecir(siradaki_yon, gecis_hakki)
                yield self.env.timeout(1)

            if self.env.now >= self.ayarlar.toplam_sure_saniye():
                return

            self.aktif_isik = "sari"
            yield self.env.timeout(self.ayarlar.sari_isik_suresi)

            if siradaki_yon == "kuzey_guney":
                siradaki_yon = "dogu_bati"
            else:
                siradaki_yon = "kuzey_guney"

    def metrikleri_hazirla(self):
        tum_beklemeler = self.bekleme_sureleri["kuzey_guney"] + self.bekleme_sureleri["dogu_bati"]
        toplam_uretilen = self.uretilen_arac_sayisi["kuzey_guney"] + self.uretilen_arac_sayisi["dogu_bati"]
        toplam_gecen = self.gecen_arac_sayisi["kuzey_guney"] + self.gecen_arac_sayisi["dogu_bati"]
        kalan_kuyruk = len(self.kuyruklar["kuzey_guney"]) + len(self.kuyruklar["dogu_bati"])

        ortalama_bekleme_kuzey_guney = mean(self.bekleme_sureleri["kuzey_guney"]) if self.bekleme_sureleri["kuzey_guney"] else 0.0
        ortalama_bekleme_dogu_bati = mean(self.bekleme_sureleri["dogu_bati"]) if self.bekleme_sureleri["dogu_bati"] else 0.0
        ortalama_bekleme_toplam = mean(tum_beklemeler) if tum_beklemeler else 0.0

        gecmis_df = pd.DataFrame(self.gecmis_kayitlari)
        if gecmis_df.empty:
            ortalama_kuyruk_toplam = 0.0
            maksimum_kuyruk_toplam = 0.0
        else:
            toplam_kuyruk_serisi = gecmis_df["kuzey_guney_kuyruk"] + gecmis_df["dogu_bati_kuyruk"]
            ortalama_kuyruk_toplam = float(toplam_kuyruk_serisi.mean())
            maksimum_kuyruk_toplam = float(toplam_kuyruk_serisi.max())

        gecis_orani = (toplam_gecen / toplam_uretilen) if toplam_uretilen else 0.0

        return {
            "uretilen_arac_sayisi": float(toplam_uretilen),
            "gecen_arac_sayisi": float(toplam_gecen),
            "kalan_kuyruk_sayisi": float(kalan_kuyruk),
            "ortalama_bekleme_kuzey_guney_saniye": round(ortalama_bekleme_kuzey_guney, 2),
            "ortalama_bekleme_dogu_bati_saniye": round(ortalama_bekleme_dogu_bati, 2),
            "ortalama_bekleme_toplam_saniye": round(ortalama_bekleme_toplam, 2),
            "maksimum_kuyruk_kuzey_guney": float(self.en_buyuk_kuyruk["kuzey_guney"]),
            "maksimum_kuyruk_dogu_bati": float(self.en_buyuk_kuyruk["dogu_bati"]),
            "maksimum_kuyruk_toplam": maksimum_kuyruk_toplam,
            "ortalama_kuyruk_toplam": round(ortalama_kuyruk_toplam, 2),
            "gecis_orani": round(gecis_orani, 3),
        }

    def calistir(self):
        self.env.process(self.arac_uret("kuzey_guney"))
        self.env.process(self.arac_uret("dogu_bati"))
        self.env.process(self.durum_kaydet())
        self.env.process(self.isik_dongusu())

        self.env.run(until=self.ayarlar.toplam_sure_saniye())
        print(f"{self.kontrol_tipi} simulasyonu bitti")

        return {
            "kontrol_tipi": self.kontrol_tipi,
            "metrikler": self.metrikleri_hazirla(),
            "gecmis": pd.DataFrame(self.gecmis_kayitlari),
        }


def kontrolleri_karsilastir(ayarlar=None):
    if ayarlar is None:
        ayarlar = SimulasyonAyarlari()

    sabit_sonuc = TrafikSimulasyonu("sabit", ayarlar=ayarlar).calistir()
    bulanik_sonuc = TrafikSimulasyonu("bulanik", ayarlar=ayarlar).calistir()

    metrikler = pd.DataFrame(
        [
            {"kontrol_tipi": "Sabit Sureli", **sabit_sonuc["metrikler"]},
            {"kontrol_tipi": "Bulanik Mantik", **bulanik_sonuc["metrikler"]},
        ]
    )

    gecmisler = {
        "sabit": sabit_sonuc["gecmis"],
        "bulanik": bulanik_sonuc["gecmis"],
    }

    return metrikler, gecmisler
