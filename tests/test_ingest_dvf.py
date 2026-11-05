"""Tests de l'ingestion DVF, sur des fichiers simulés (sans réseau)."""

import gzip

import duckdb
import pytest

from ingestion.ingest_dvf import ingest_year

HEADER = "id_mutation,date_mutation,valeur_fonciere,code_departement,type_local,surface_reelle_bati,longitude,latitude\n"
ROWS = [
    "2023-1,2023-03-01,250000,69,Appartement,52,4.83,45.76\n",
    "2023-2,2023-04-12,410000.5,69,Maison,98,4.90,45.80\n",
    "2023-3,2023-05-02,180000,01,Maison,80,5.20,46.20\n",   # autre département : doit être exclu
    "2023-4,2023-06-20,,69,,,,\n",                           # ligne incomplète : gardée telle quelle en bronze
]


@pytest.fixture
def full_file(tmp_path):
    path = tmp_path / "full.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(HEADER + "".join(ROWS))
    return path.as_posix()


def test_filtre_departement_et_tracabilite(tmp_path, full_file):
    con = duckdb.connect()
    n = ingest_year(con, 2023, "69", tmp_path / "out", sources=[full_file])
    assert n == 3
    df = con.execute(f"SELECT * FROM '{(tmp_path / 'out/annee=2023/dep=69.parquet').as_posix()}'").fetchall()
    cols = [d[0] for d in con.description]
    assert "_source" in cols and "_ingere_le" in cols


def test_bascule_sur_fichier_france_si_departement_absent(tmp_path, full_file):
    con = duckdb.connect()
    missing = (tmp_path / "absent.csv.gz").as_posix()
    n = ingest_year(con, 2023, "69", tmp_path / "out", sources=[missing, full_file])
    assert n == 3
    assert not list((tmp_path / "out").rglob("*.tmp.parquet"))  # pas de fichier temporaire laissé


def test_tout_en_texte_aucune_perte(tmp_path, full_file):
    con = duckdb.connect()
    ingest_year(con, 2023, "69", tmp_path / "out", sources=[full_file])
    types = con.execute(f"DESCRIBE SELECT * FROM '{(tmp_path / 'out/annee=2023/dep=69.parquet').as_posix()}'").fetchall()
    assert {t[1] for t in types if not t[0].startswith("_") and t[0] != "annee"} == {"VARCHAR"}  # « annee » vient du nom du dossier
    val = con.execute(f"SELECT valeur_fonciere FROM '{(tmp_path / 'out/annee=2023/dep=69.parquet').as_posix()}' WHERE id_mutation='2023-2'").fetchone()[0]
    assert val == "410000.5"


def test_echec_si_aucune_source(tmp_path):
    con = duckdb.connect()
    with pytest.raises(RuntimeError):
        ingest_year(con, 2023, "69", tmp_path / "out", sources=[(tmp_path / "x.csv.gz").as_posix()])
