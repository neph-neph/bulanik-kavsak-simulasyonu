# SUMO icin ag dosyalari (.nod, .edg, .rou, .sumocfg) uretici.
# SUMO yukluyse netconvert ile .net.xml de derlenir.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

from ..data.profile import IntersectionProfile


def _yaz(yol: Path, icerik: str):
    yol.write_text(icerik, encoding="utf-8")


def _xml_basligi() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n'


def _dugumler_xml(dugumler: List[Tuple[str, float, float, str]]) -> str:
    parcalar = [_xml_basligi(), "<nodes>"]
    for ad, x, y, tip in dugumler:
        parcalar.append(f'  <node id="{ad}" x="{x}" y="{y}" type="{tip}"/>')
    parcalar.append("</nodes>")
    return "\n".join(parcalar)


def _kenarlar_xml(kenarlar: List[Tuple[str, str, str, int]]) -> str:
    parcalar = [_xml_basligi(), "<edges>"]
    for kid, baslangic, son, seritler in kenarlar:
        parcalar.append(
            f'  <edge id="{kid}" from="{baslangic}" to="{son}" numLanes="{seritler}" speed="13.89"/>'
        )
    parcalar.append("</edges>")
    return "\n".join(parcalar)


def _rotalar_xml(akislar) -> str:
    """akislar: (id, edges_listesi, begin, end, vehsPerHour)
    edges_listesi: bosluklu str veya liste; rotada ziyaret edilen TUM kenarlar sirayla.
    """
    parcalar = [_xml_basligi(), "<routes>"]
    parcalar.append(
        '  <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" maxSpeed="13.89"/>'
    )
    for akis in akislar:
        id_, edges, begin, end, vph = akis
        if isinstance(edges, (list, tuple)):
            edges_str = " ".join(edges)
        else:
            edges_str = edges
        rota_id = f"route_{id_}"
        parcalar.append(f'  <route id="{rota_id}" edges="{edges_str}"/>')
        parcalar.append(
            f'  <flow id="{id_}" route="{rota_id}" begin="{begin}" end="{end}" vehsPerHour="{vph:.1f}" type="car"/>'
        )
    parcalar.append("</routes>")
    return "\n".join(parcalar)


def _sumocfg_xml(net_dosyasi: str, rou_dosyasi: str, sure: float) -> str:
    return (
        _xml_basligi()
        + f"""<configuration>
  <input>
    <net-file value="{net_dosyasi}"/>
    <route-files value="{rou_dosyasi}"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="{int(sure)}"/>
    <step-length value="1"/>
  </time>
</configuration>
"""
    )


def _netconvert_calistir(out_dir: Path, baz_ad: str = "network") -> bool:
    """netconvert varsa .nod + .edg → .net.xml derler."""
    try:
        proc = subprocess.run(
            [
                "netconvert",
                "-n", str(out_dir / f"{baz_ad}.nod.xml"),
                "-e", str(out_dir / f"{baz_ad}.edg.xml"),
                "-o", str(out_dir / f"{baz_ad}.net.xml"),
                "--no-warnings",
            ],
            capture_output=True,
            timeout=60,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _profil_saatlik_ortalama(profil: IntersectionProfile, yon: str, baslangic_saati: int, dakika: int) -> float:
    """Profilden simülasyon süresi içinde tahmini araç/saat döner (basit ortalama)."""
    saatler = list(profil.yon_profilleri[yon].saatlik_arac_sayisi)
    n_saat = max(1, dakika // 60)
    secilen = []
    for i in range(n_saat + 1):
        secilen.append(saatler[(baslangic_saati + i) % 24])
    return sum(secilen) / len(secilen)


def sumo_tek_kavsak_olustur(
    out_dir: Path,
    profil: IntersectionProfile,
    baslangic_saati: int = 7,
    sure_dakika: int = 30,
) -> Path:
    """Tek kavşak için SUMO dosyalarını üretir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dugumler = [
        ("Kuzey", 0.0, 200.0, "priority"),
        ("Guney", 0.0, -200.0, "priority"),
        ("Dogu", 200.0, 0.0, "priority"),
        ("Bati", -200.0, 0.0, "priority"),
        ("Merkez", 0.0, 0.0, "traffic_light"),
    ]
    kenarlar = [
        ("K_in", "Kuzey", "Merkez", 1), ("K_out", "Merkez", "Kuzey", 1),
        ("G_in", "Guney", "Merkez", 1), ("G_out", "Merkez", "Guney", 1),
        ("D_in", "Dogu", "Merkez", 1), ("D_out", "Merkez", "Dogu", 1),
        ("B_in", "Bati", "Merkez", 1), ("B_out", "Merkez", "Bati", 1),
    ]

    _yaz(out_dir / "network.nod.xml", _dugumler_xml(dugumler))
    _yaz(out_dir / "network.edg.xml", _kenarlar_xml(kenarlar))

    sure = sure_dakika * 60
    kg_vph = _profil_saatlik_ortalama(profil, "kuzey_guney", baslangic_saati, sure_dakika)
    db_vph = _profil_saatlik_ortalama(profil, "dogu_bati", baslangic_saati, sure_dakika)

    akislar = [
        ("akis_KG", ["K_in", "G_out"], 0.0, sure, kg_vph),
        ("akis_GK", ["G_in", "K_out"], 0.0, sure, kg_vph),
        ("akis_DB", ["D_in", "B_out"], 0.0, sure, db_vph),
        ("akis_BD", ["B_in", "D_out"], 0.0, sure, db_vph),
    ]
    _yaz(out_dir / "network.rou.xml", _rotalar_xml(akislar))

    derlendi = _netconvert_calistir(out_dir)
    cfg = _sumocfg_xml(
        "network.net.xml" if derlendi else "network.edg.xml",
        "network.rou.xml",
        sure,
    )
    _yaz(out_dir / "scenario.sumocfg", cfg)

    okuma = out_dir / "README.txt"
    _yaz(
        okuma,
        "SUMO senaryosu\n"
        "===============\n"
        f"netconvert {'BAŞARILI' if derlendi else 'çalıştırılamadı (SUMO yüklü değil olabilir; .edg/.nod dosyaları hazır)'}.\n"
        "Çalıştırmak için:\n"
        "  sumo -c scenario.sumocfg\n"
        "  sumo-gui -c scenario.sumocfg  (görsel)\n"
        "Bulanık kontrolcüyle (TraCI):\n"
        "  python -m src.sumo.runner --scenario {0}/scenario.sumocfg\n".format(out_dir),
    )

    return out_dir


def sumo_koridor_olustur(
    out_dir: Path,
    profiller: List[IntersectionProfile],
    baslangic_saati: int = 7,
    sure_dakika: int = 30,
    kavsaklar_arasi_mesafe: float = 400.0,
) -> Path:
    """N kavşaktan oluşan koridor için SUMO ağı üretir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(profiller)

    dugumler = []
    for i in range(n):
        dugumler.append((f"K{i+1}", i * kavsaklar_arasi_mesafe, 0.0, "traffic_light"))
    dugumler.append(("BatiUc", -kavsaklar_arasi_mesafe, 0.0, "priority"))
    dugumler.append(("DoguUc", n * kavsaklar_arasi_mesafe, 0.0, "priority"))
    for i in range(n):
        dugumler.append((f"K{i+1}_K", i * kavsaklar_arasi_mesafe, 200.0, "priority"))
        dugumler.append((f"K{i+1}_G", i * kavsaklar_arasi_mesafe, -200.0, "priority"))

    kenarlar = [
        ("e_bati_in", "BatiUc", "K1", 1), ("e_bati_out", "K1", "BatiUc", 1),
        ("e_dogu_in", "DoguUc", f"K{n}", 1), ("e_dogu_out", f"K{n}", "DoguUc", 1),
    ]
    for i in range(n - 1):
        kenarlar.append((f"e_K{i+1}_K{i+2}", f"K{i+1}", f"K{i+2}", 1))
        kenarlar.append((f"e_K{i+2}_K{i+1}", f"K{i+2}", f"K{i+1}", 1))
    for i in range(n):
        kenarlar.append((f"e_K{i+1}_kuz_in", f"K{i+1}_K", f"K{i+1}", 1))
        kenarlar.append((f"e_K{i+1}_kuz_out", f"K{i+1}", f"K{i+1}_K", 1))
        kenarlar.append((f"e_K{i+1}_guney_in", f"K{i+1}_G", f"K{i+1}", 1))
        kenarlar.append((f"e_K{i+1}_guney_out", f"K{i+1}", f"K{i+1}_G", 1))

    _yaz(out_dir / "network.nod.xml", _dugumler_xml(dugumler))
    _yaz(out_dir / "network.edg.xml", _kenarlar_xml(kenarlar))

    sure = sure_dakika * 60
    akislar = []
    # Doğu-batı ana akış: tüm kavşakları geçen full path
    db_vph = _profil_saatlik_ortalama(profiller[0], "dogu_bati", baslangic_saati, sure_dakika)
    # Doğuya: BatiUc -> K1 -> K2 -> ... -> Kn -> DoguUc
    dogu_edges = ["e_bati_in"]
    for i in range(n - 1):
        dogu_edges.append(f"e_K{i+1}_K{i+2}")
    dogu_edges.append("e_dogu_out")
    # Batıya: DoguUc -> Kn -> ... -> K1 -> BatiUc
    bati_edges = ["e_dogu_in"]
    for i in range(n - 1, 0, -1):
        bati_edges.append(f"e_K{i+1}_K{i}")
    bati_edges.append("e_bati_out")
    akislar.append(("akis_DB_dogu", dogu_edges, 0.0, sure, db_vph))
    akislar.append(("akis_DB_bati", bati_edges, 0.0, sure, db_vph))
    # Her kavşakta KG akışı (kuzey -> güney ve tersi, 2 kenar)
    for i, profil in enumerate(profiller):
        kg = _profil_saatlik_ortalama(profil, "kuzey_guney", baslangic_saati, sure_dakika)
        akislar.append((f"akis_K{i+1}_kg", [f"e_K{i+1}_kuz_in", f"e_K{i+1}_guney_out"], 0.0, sure, kg))
        akislar.append((f"akis_K{i+1}_gk", [f"e_K{i+1}_guney_in", f"e_K{i+1}_kuz_out"], 0.0, sure, kg))

    _yaz(out_dir / "network.rou.xml", _rotalar_xml(akislar))

    derlendi = _netconvert_calistir(out_dir)
    cfg = _sumocfg_xml(
        "network.net.xml" if derlendi else "network.edg.xml",
        "network.rou.xml",
        sure,
    )
    _yaz(out_dir / "scenario.sumocfg", cfg)
    return out_dir


def sumo_grid_olustur(
    out_dir: Path,
    profiller: Dict[str, IntersectionProfile],
    baslangic_saati: int = 7,
    sure_dakika: int = 30,
    blok_mesafesi: float = 400.0,
) -> Path:
    """2x2 grid için SUMO ağı."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    konum = {
        "K11": (0.0, blok_mesafesi),
        "K12": (blok_mesafesi, blok_mesafesi),
        "K21": (0.0, 0.0),
        "K22": (blok_mesafesi, 0.0),
    }
    dugumler = []
    for ad, (x, y) in konum.items():
        dugumler.append((ad, x, y, "traffic_light"))
    cevre = [
        ("U_K11", -blok_mesafesi, blok_mesafesi),
        ("U_K12", 2 * blok_mesafesi, blok_mesafesi),
        ("U_K21", -blok_mesafesi, 0.0),
        ("U_K22", 2 * blok_mesafesi, 0.0),
        ("U_K11N", 0.0, 2 * blok_mesafesi),
        ("U_K12N", blok_mesafesi, 2 * blok_mesafesi),
        ("U_K21S", 0.0, -blok_mesafesi),
        ("U_K22S", blok_mesafesi, -blok_mesafesi),
    ]
    for ad, x, y in cevre:
        dugumler.append((ad, x, y, "priority"))

    kenarlar = []
    # iç bağlar
    iç_baglar = [
        ("K11", "K12"), ("K12", "K11"),
        ("K21", "K22"), ("K22", "K21"),
        ("K11", "K21"), ("K21", "K11"),
        ("K12", "K22"), ("K22", "K12"),
    ]
    for a, b in iç_baglar:
        kenarlar.append((f"e_{a}_{b}", a, b, 1))
    # dış girişler
    dis_baglar = [
        ("U_K11", "K11"), ("K11", "U_K11"),
        ("U_K12", "K12"), ("K12", "U_K12"),
        ("U_K21", "K21"), ("K21", "U_K21"),
        ("U_K22", "K22"), ("K22", "U_K22"),
        ("U_K11N", "K11"), ("K11", "U_K11N"),
        ("U_K12N", "K12"), ("K12", "U_K12N"),
        ("U_K21S", "K21"), ("K21", "U_K21S"),
        ("U_K22S", "K22"), ("K22", "U_K22S"),
    ]
    for a, b in dis_baglar:
        kenarlar.append((f"e_{a}_{b}", a, b, 1))

    _yaz(out_dir / "network.nod.xml", _dugumler_xml(dugumler))
    _yaz(out_dir / "network.edg.xml", _kenarlar_xml(kenarlar))

    sure = sure_dakika * 60
    # Doğu-batı akışı her satır için (uçtan uca, 3 kenar)
    # Üst satır (K11-K12)
    db_ust = _profil_saatlik_ortalama(profiller["K11"], "dogu_bati", baslangic_saati, sure_dakika)
    db_alt = _profil_saatlik_ortalama(profiller["K21"], "dogu_bati", baslangic_saati, sure_dakika)
    kg_sol = _profil_saatlik_ortalama(profiller["K11"], "kuzey_guney", baslangic_saati, sure_dakika)
    kg_sag = _profil_saatlik_ortalama(profiller["K12"], "kuzey_guney", baslangic_saati, sure_dakika)

    akislar = [
        # Doğuya doğru üst satır: U_K11 -> K11 -> K12 -> U_K12
        ("akis_ust_dogu", ["e_U_K11_K11", "e_K11_K12", "e_K12_U_K12"], 0.0, sure, db_ust),
        # Batıya doğru üst satır
        ("akis_ust_bati", ["e_U_K12_K12", "e_K12_K11", "e_K11_U_K11"], 0.0, sure, db_ust),
        # Doğuya doğru alt satır
        ("akis_alt_dogu", ["e_U_K21_K21", "e_K21_K22", "e_K22_U_K22"], 0.0, sure, db_alt),
        # Batıya doğru alt satır
        ("akis_alt_bati", ["e_U_K22_K22", "e_K22_K21", "e_K21_U_K21"], 0.0, sure, db_alt),
        # Güneye doğru sol kolon: U_K11N -> K11 -> K21 -> U_K21S
        ("akis_sol_guney", ["e_U_K11N_K11", "e_K11_K21", "e_K21_U_K21S"], 0.0, sure, kg_sol),
        # Kuzeye doğru sol kolon
        ("akis_sol_kuzey", ["e_U_K21S_K21", "e_K21_K11", "e_K11_U_K11N"], 0.0, sure, kg_sol),
        # Güneye doğru sağ kolon
        ("akis_sag_guney", ["e_U_K12N_K12", "e_K12_K22", "e_K22_U_K22S"], 0.0, sure, kg_sag),
        # Kuzeye doğru sağ kolon
        ("akis_sag_kuzey", ["e_U_K22S_K22", "e_K22_K12", "e_K12_U_K12N"], 0.0, sure, kg_sag),
    ]

    _yaz(out_dir / "network.rou.xml", _rotalar_xml(akislar))

    derlendi = _netconvert_calistir(out_dir)
    cfg = _sumocfg_xml(
        "network.net.xml" if derlendi else "network.edg.xml",
        "network.rou.xml",
        sure,
    )
    _yaz(out_dir / "scenario.sumocfg", cfg)
    return out_dir
