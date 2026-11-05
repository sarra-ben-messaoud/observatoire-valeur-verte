"""Exploration de l'API DPE de l'ADEME, avant d'écrire l'ingestion.

Objectif : identifier le bon jeu de données et les noms exacts des colonnes,
plutôt que de les supposer.

    python -m ingestion.explore_dpe
"""

import json

import requests

import config

SEARCH = "dpe logements existants"


def main():
    print("1. Jeux de données DPE publiés par l'ADEME\n")
    r = requests.get(f"{config.ADEME_API}/datasets", params={"q": SEARCH, "size": 10}, timeout=30)
    r.raise_for_status()
    datasets = r.json().get("results", [])
    for d in datasets:
        print(f"  - id: {d.get('id')}  |  {d.get('title')}  |  {d.get('count', '?')} lignes")

    candidate = next((d for d in datasets if "existant" in (d.get("title") or "").lower()
                      and "juillet 2021" in (d.get("title") or "").lower()), datasets[0] if datasets else None)
    if not candidate:
        print("Aucun jeu de données trouvé.")
        return
    ds = candidate["id"]
    print(f"\n2. Colonnes du jeu de données retenu : {ds}\n")
    schema = requests.get(f"{config.ADEME_API}/datasets/{ds}/schema", timeout=30).json()
    keywords = ("ban", "dpe", "ges", "date", "surface", "type", "batiment", "commune", "insee",
                "postal", "departement", "geo", "construction", "niveau", "adresse", "logement")
    for col in schema:
        key = col.get("key", "")
        if any(k in key.lower() for k in keywords):
            print(f"  - {key}  ({col.get('type')})  {(col.get('title') or '')[:60]}")
    print(f"\n  ({len(schema)} colonnes au total)")

    print("\n3. Exemple de 2 lignes dans le Rhône\n")
    dep_col = next((c["key"] for c in schema if "departement" in c.get("key", "").lower()), None)
    params = {"size": 2}
    if dep_col:
        params["qs"] = f'{dep_col}:"69"'
    lines = requests.get(f"{config.ADEME_API}/datasets/{ds}/lines", params=params, timeout=30).json()
    print(f"  Filtre utilisé : {params.get('qs')}  ->  {lines.get('total')} DPE au total")
    for row in lines.get("results", []):
        short = {k: v for k, v in row.items() if any(w in k.lower() for w in keywords)}
        print(json.dumps(short, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()
