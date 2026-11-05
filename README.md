# 🏠 Observatoire de la valeur verte immobilière

**La performance énergétique d'un logement (DPE) influence-t-elle son prix de vente, et de combien ?**

Pipeline de données de bout en bout sur les ventes immobilières (DVF) et les diagnostics de performance
énergétique (ADEME) : ingestion, lakehouse bronze / silver / gold, transformations et tests avec dbt,
orchestration avec Airflow, dashboard Power BI et analyse statistique.

> 🚧 Projet en cours de construction. Périmètre de la version 1 : le Rhône, ventes 2022-2025.

- Cadrage complet (besoin, sources, architecture, plan) : [`docs/cadrage.md`](docs/cadrage.md)

## Avancement

| Étape | Statut |
| --- | --- |
| 1. Cadrage | ✅ |
| 2. Ingestion bronze (DVF, DPE) | ✅ |
| 3. Silver et rapprochement DVF ↔ DPE | ✅ |
| 4. Gold et tests de qualité | ⏳ |
| 5. Orchestration (Airflow) et CI (GitHub Actions) | ⏳ |
| 6. Dashboard Power BI | ⏳ |
| 7. Analyse de la valeur verte | ⏳ |
| 8. Passage à l'échelle (France entière) | ⏳ |

## Premiers résultats (Rhône, 2022-2025)

| Étape | Volume |
| --- | --- |
| Lignes DVF ingérées | 354 101 |
| Ventes d'un seul logement (hors neuf) | 85 431 |
| DPE de logements ingérés | 517 849 |
| Ventes rapprochées d'un DPE | 53 109 (62 %) |
| dont rapprochements fiables (utilisés pour l'analyse) | 30 491 |

**Le rapprochement en cascade** — DVF et les DPE n'ont aucun identifiant commun :
1. **Clé d'adresse exacte** (97 % des rapprochements) : l'identifiant BAN des DPE (`69266_2275_00006`) est reconstruit
   côté DVF à partir du code commune, du code de voie et du numéro.
2. **Adresse normalisée** en secours : noms de voie sans accents, sans type de voie ni mots de liaison
   (« AV GENERAL DE GAULLE » et « Avenue du Général de Gaulle » → « GENERAL GAULLE »).
3. **Contrôles** : même type de logement, surface à ±10 %, DPE établi avant la vente (3 ans maximum).
4. **Fiabilité** : on écarte de l'analyse les cas où plusieurs DPE d'étiquettes différentes sont possibles,
   et ceux où un même DPE est retenu pour plusieurs ventes.

Le taux de rapprochement progresse de 57 % (2022) à 82 % (2025) pour les appartements, à mesure que
la base des DPE « nouvelle méthode » (depuis juillet 2021) se remplit.

## Lancer le projet

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (Mac/Linux : source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest                  # tests
python -m ingestion.ingest_dvf    # ingestion des ventes (DVF)
python -m ingestion.ingest_dpe    # ingestion des diagnostics énergétiques (DPE), incrémentale
cd transform
dbt build                         # transformations silver + tests de qualité
```

---
Projet personnel de **Sarra Ben Messaoud** · [LinkedIn](https://www.linkedin.com/in/sarrabenmessaoud)
