"""Étape 2 — Ingestion bronze des diagnostics de performance énergétique (API ADEME).

    python -m ingestion.ingest_dpe             # incrémental : seulement les DPE modifiés depuis la dernière fois
    python -m ingestion.ingest_dpe --full      # rechargement complet

Choix de conception :
- Pagination par curseur (lien « next » de l'API) : seule méthode fiable au-delà de 10 000 résultats.
- Incrémental : on ne redemande que les DPE créés ou modifiés depuis la date la plus récente déjà reçue.
  Chaque passage écrit un nouveau fichier « part-… » ; les doublons éventuels (un DPE modifié
  deux fois) sont résolus en silver, en gardant la version la plus récente de chaque numero_dpe.
- 35 colonnes utiles sur 230 : moins de volume, et un périmètre explicite.
- Nouvelles tentatives automatiques si l'API répond lentement ou limite le débit.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import requests

import config


def resolve_dataset_id(session) -> str:
    """Vérifie l'identifiant du jeu de données ; le retrouve par son titre s'il a changé."""
    r = session.get(f"{config.ADEME_API}/datasets/{config.DPE_DATASET_ID}", timeout=30)
    if r.status_code == 200:
        return config.DPE_DATASET_ID
    r = session.get(f"{config.ADEME_API}/datasets", params={"q": config.DPE_DATASET_TITLE, "size": 20}, timeout=30)
    r.raise_for_status()
    for d in r.json().get("results", []):
        if d.get("title", "").strip() == config.DPE_DATASET_TITLE:
            print(f"  Identifiant du jeu de données mis à jour : {d['id']}")
            return d["id"]
    raise RuntimeError("Jeu de données DPE introuvable : relancer ingestion/explore_dpe.py")


def get_with_retry(session, url, params=None, attempts=6):
    for attempt in range(attempts):
        try:
            r = session.get(url, params=params, timeout=120)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as error:
            if attempt == attempts - 1:
                raise
            wait = 2 ** attempt
            print(f"    nouvelle tentative dans {wait}s ({error})")
            time.sleep(wait)


def fetch_pages(session, dataset_id: str, query: str):
    """Renvoie les lignes page par page, en suivant le lien « next »."""
    url = f"{config.ADEME_API}/datasets/{dataset_id}/lines"
    params = {"size": config.DPE_PAGE_SIZE, "qs": query, "select": ",".join(config.DPE_COLUMNS)}
    page = get_with_retry(session, url, params)
    total = page.get("total", 0)
    yield total, page.get("results", [])
    while page.get("next") and page.get("results"):
        page = get_with_retry(session, page["next"])
        yield total, page.get("results", [])


def last_modification(dep_dir: Path) -> str | None:
    """Date de modification la plus récente déjà ingérée (pour l'incrémental)."""
    parts = list(dep_dir.glob("part-*.parquet"))
    if not parts:
        return None
    con = duckdb.connect()
    return con.execute(f"SELECT max(date_derniere_modification_dpe) FROM '{dep_dir.as_posix()}/part-*.parquet'").fetchone()[0]


class PartWriter:
    """Écrit les pages au fil de l'eau dans un fichier temporaire (mémoire constante),
    puis les convertit en un seul fichier Parquet, toutes colonnes en texte (bronze = brut)."""

    def __init__(self, dep_dir: Path):
        dep_dir.mkdir(parents=True, exist_ok=True)
        self.stamp = datetime.now(timezone.utc)
        self.dep_dir = dep_dir
        self.tmp = dep_dir / f".tmp-{self.stamp:%Y%m%d%H%M%S%f}.jsonl"
        self.file = open(self.tmp, "w", encoding="utf-8")
        self.count = 0

    def write(self, rows: list[dict]) -> None:
        for row in rows:
            clean = {c: (None if row.get(c) is None else str(row.get(c))) for c in config.DPE_COLUMNS}
            self.file.write(json.dumps(clean, ensure_ascii=False) + "\n")
        self.count += len(rows)

    def close(self) -> Path | None:
        self.file.close()
        if self.count == 0:
            self.tmp.unlink()
            return None
        target = self.dep_dir / f"part-{self.stamp:%Y%m%d%H%M%S%f}.parquet"
        columns = ", ".join(f"'{c}': 'VARCHAR'" for c in config.DPE_COLUMNS)
        duckdb.connect().execute(f"""
            COPY (
                SELECT *, TIMESTAMP '{self.stamp:%Y-%m-%d %H:%M:%S}' AS _ingere_le
                FROM read_json('{self.tmp.as_posix()}', format = 'newline_delimited', columns = {{{columns}}})
            ) TO '{target.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """)
        self.tmp.unlink()
        return target


def ingest_departement(session, dataset_id: str, dep: str, out_dir: Path, full: bool = False) -> int:
    dep_dir = out_dir / f"dep={dep}"
    since = None if full else last_modification(dep_dir)
    query = f'code_departement_ban:"{dep}"'
    if since:
        query += f" AND date_derniere_modification_dpe:>={since}"
        print(f"  dep {dep} : DPE modifiés depuis le {since}")
    old_parts = list(dep_dir.glob("part-*.parquet")) if full else []

    writer, start = PartWriter(dep_dir), time.perf_counter()
    try:
        for total, batch in fetch_pages(session, dataset_id, query):
            writer.write(batch)
            print(f"    {writer.count:,} / {total:,} DPE récupérés")
    except BaseException:
        writer.file.close()
        writer.tmp.unlink(missing_ok=True)  # pas de fichier partiel en cas d'échec
        raise
    target = writer.close()
    for old in old_parts:   # rechargement complet : on ne supprime l'ancien qu'après un succès
        if old != target:
            old.unlink()
    if target is None:
        print(f"  dep {dep} : rien de nouveau")
        return 0
    print(f"  dep {dep} : {writer.count:,} DPE écrits en {time.perf_counter() - start:.0f}s → {target.name}")
    return writer.count


def main():
    config.preparer_dossiers()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Rechargement complet au lieu de l'incrémental")
    args = parser.parse_args()
    session = requests.Session()
    dataset_id = resolve_dataset_id(session)
    print(f"Ingestion DPE (bronze) — jeu de données {dataset_id}")
    total = sum(ingest_departement(session, dataset_id, dep, config.BRONZE_DIR / "dpe", args.full)
                for dep in config.DEPARTEMENTS)
    print(f"Terminé : {total:,} DPE ingérés.")


if __name__ == "__main__":
    main()
