# SUMO senaryosunu TraCI uzerinden bulanik kontrolcuyle calistirir.
# Kullanim: py -m src.sumo.runner --scenario <yol>.sumocfg [--gui]

import argparse
import importlib
import os


def sumo_mevcut_mu() -> bool:
    try:
        importlib.import_module("traci")
        return True
    except ImportError:
        return False


def sumo_bulanik_calistir(
    sumocfg_yolu: str,
    sumo_binary: str = "sumo-gui",
    min_yesil: float = 10.0,
    max_yesil: float = 50.0,
):
    # SUMO'yu baslat, her isigin yesil fazinda kuyruga bakip bulanik suresine ayarla
    if not sumo_mevcut_mu():
        raise RuntimeError("traci yuklu degil. Lutfen 'pip install traci sumolib' calistirin.")
    import traci
    from ..controllers.fuzzy import yesil_sure_hesapla

    traci.start([sumo_binary, "-c", sumocfg_yolu, "--no-warnings", "--no-step-log"])

    # Her isik icin: faz tipini (green/yellow) ve her fazin kontrol ettigi seritleri onbellege al
    faz_meta = {}
    for tls_id in traci.trafficlight.getIDList():
        program = traci.trafficlight.getAllProgramLogics(tls_id)[0]
        # Yesil fazlari belirle (en az bir 'G' iceren faz)
        yesil_indeksler = [i for i, p in enumerate(program.phases) if "G" in p.state.upper()]
        faz_meta[tls_id] = {
            "yesil_indeksler": set(yesil_indeksler),
            "kontrol_seritleri": list(set(traci.trafficlight.getControlledLanes(tls_id))),
            "son_mudahale_faz": -1,
        }

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            try:
                traci.simulationStep()
            except Exception:
                break

            for tls_id, meta in faz_meta.items():
                try:
                    su_an_faz = traci.trafficlight.getPhase(tls_id)
                except Exception:
                    continue

                # Sadece yesil fazlardayken mudahale et (sari/kirmizi gecislerini bozma)
                if su_an_faz not in meta["yesil_indeksler"]:
                    meta["son_mudahale_faz"] = -1
                    continue

                # Bu yesil fazda zaten mudahale ettiysek tekrar yapma
                if meta["son_mudahale_faz"] == su_an_faz:
                    continue

                # Yon kuyruk ve bekleme verilerini topla
                seritler = meta["kontrol_seritleri"]
                if not seritler:
                    continue
                kuyruk = {l: traci.lane.getLastStepHaltingNumber(l) for l in seritler}
                bekleme = {l: traci.lane.getWaitingTime(l) for l in seritler}

                aktif_serit = max(kuyruk, key=kuyruk.get)
                karsi_serit = min(kuyruk, key=kuyruk.get)

                # Bulanik yesil suresini hesapla
                yesil = yesil_sure_hesapla(
                    kuyruk[aktif_serit],
                    bekleme[aktif_serit],
                    karsi_kuyruk=kuyruk[karsi_serit],
                    min_yesil=min_yesil,
                    max_yesil=max_yesil,
                )
                # Mevcut yesil fazin kalan suresini bulanik degere ayarla
                try:
                    traci.trafficlight.setPhaseDuration(tls_id, float(yesil))
                    meta["son_mudahale_faz"] = su_an_faz
                except Exception:
                    pass
    finally:
        try:
            traci.close()
        except Exception:
            pass


def _ana():
    parser = argparse.ArgumentParser(description="SUMO senaryosunu bulanik kontrolcuyle calistir.")
    parser.add_argument("--scenario", required=True, help=".sumocfg dosyasinin yolu")
    parser.add_argument("--gui", action="store_true", help="sumo-gui kullan")
    args = parser.parse_args()

    sumo_bin = "sumo-gui" if args.gui else "sumo"
    sumo_bulanik_calistir(args.scenario, sumo_binary=sumo_bin)


if __name__ == "__main__":
    _ana()
