"""Paramètres du projet, regroupés à un seul endroit."""

from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"

# Périmètre de la version 1
DEPARTEMENTS = ["69"]                 # Rhône ; on élargira à l'étape 8
ANNEES_DVF = [2022, 2023, 2024, 2025] # période couverte par DVF et par les DPE « nouvelle méthode »

# Sources
DVF_BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"
ADEME_API = "https://data.ademe.fr/data-fair/api/v1"

# DPE logements existants (depuis juillet 2021), jeu de données ADEME identifié avec ingestion/explore_dpe.py
DPE_DATASET_ID = "meg-83tjwtg8dyz4vv7h1dqe"
DPE_DATASET_TITLE = "DPE Logements existants (depuis juillet 2021)"  # pour le retrouver si l'identifiant change
DPE_PAGE_SIZE = 10000

# Colonnes utiles au projet (sur 230) : identification, dates, étiquettes, logement, adresse BAN, consommation
DPE_COLUMNS = [
    "numero_dpe", "date_derniere_modification_dpe", "date_etablissement_dpe", "date_fin_validite_dpe",
    "numero_dpe_remplace", "numero_dpe_immeuble_associe", "modele_dpe", "version_dpe", "methode_application_dpe",
    "etiquette_dpe", "etiquette_ges", "conso_5_usages_par_m2_ep", "emission_ges_5_usages_par_m2", "cout_total_5_usages",
    "type_batiment", "typologie_logement", "surface_habitable_logement", "nombre_niveau_logement",
    "annee_construction", "periode_construction", "position_logement_dans_immeuble", "complement_adresse_logement",
    "type_installation_chauffage", "type_energie_principale_chauffage",
    "identifiant_ban", "adresse_ban", "numero_voie_ban", "nom_rue_ban", "code_postal_ban", "code_insee_ban",
    "nom_commune_ban", "code_departement_ban", "score_ban", "statut_geocodage", "_geopoint",
]
