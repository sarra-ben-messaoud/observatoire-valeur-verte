"""Étape 2 — Ingestion bronze des ventes immobilières (DVF géolocalisées).

Pour chaque année, on récupère les ventes du département et on les écrit telles quelles
au format Parquet, avec deux colonnes de traçabilité (_source, _ingere_le).

    python -m ingestion.ingest_dvf            # ingère ce qui manque
    python -m ingestion.ingest_dvf --force    # réingère tout

Choix de conception :
- Bronze = données brutes : on ne nettoie rien ici, on garde tout (le nettoyage est fait en silver avec dbt).
- Toutes les colonnes sont lues en texte : aucune conversion silencieuse ne peut perdre d'information.
- Idempotent : relancer le script ne crée pas de doublons, il saute les fichiers déjà présents.
- Fichier départemental d'abord ; si absent, fichier France entière filtré par DuckDB.
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

import config


def sources_for(annee: int, dep: str) -> list[str]:
    """URL candidates, de la plus légère à la plus lourde."""
    base = f"{config.DVF_BASE_URL}/{annee}"
    return [f"{base}/departements/{dep}.csv.gz", f"{base}/full.csv.gz"]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")  # lecture directe de fichiers en ligne
    return con


def ingest_year(con, annee: int, dep: str, out_dir: Path, sources: list[str] | None = None) -> int:
    """Écrit data/bronze/dvf/annee=AAAA/dep=XX.parquet et renvoie le nombre de lignes."""
    target = out_dir / f"annee={annee}" / f"dep={dep}.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp.parquet")
    last_error = None

    for src in sources or sources_for(annee, dep):
        try:
            start = time.perf_counter()
            con.execute(f"""
                COPY (
                    SELECT *, '{src}' AS _source, TIMESTAMP '{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}' AS _ingere_le
                    FROM read_csv('{src}', header = true, all_varchar = true)
                    WHERE code_departement = '{dep}'
                ) TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
            """)
            tmp.replace(target)  # écriture atomique : pas de fichier à moitié écrit
            n = con.execute(f"SELECT count(*) FROM '{target.as_posix()}'").fetchone()[0]
            print(f"  {annee} · dep {dep} : {n:,} lignes en {time.perf_counter() - start:.0f}s ({src.rsplit('/', 2)[-1]})")
            return n
        except duckdb.Error as error:
            last_error = error
            tmp.unlink(missing_ok=True)
            print(f"  {annee} · source indisponible, essai suivant ({src.rsplit('/', 3)[-2:]})")
    raise RuntimeError(f"Aucune source DVF disponible pour {annee} : {last_error}")


def main():
    config.preparer_dossiers()
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Réingérer même si le fichier existe")
    args = parser.parse_args()

    out_dir = config.BRONZE_DIR / "dvf"
    con = connect()
    total = 0
    print("Ingestion DVF (bronze)")
    for dep in config.DEPARTEMENTS:
        for annee in config.ANNEES_DVF:
            target = out_dir / f"annee={annee}" / f"dep={dep}.parquet"
            if target.exists() and not args.force:
                print(f"  {annee} · dep {dep} : déjà présent, ignoré")
                continue
            total += ingest_year(con, annee, dep, out_dir)
    print(f"Terminé : {total:,} nouvelles lignes. Fichiers dans {out_dir}")


if __name__ == "__main__":
    main()
