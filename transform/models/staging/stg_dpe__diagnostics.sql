-- DPE typés, une ligne par numéro de DPE.
-- L'ingestion incrémentale peut avoir reçu plusieurs versions d'un même DPE : on garde la plus récente.
select
    numero_dpe,
    try_cast(date_etablissement_dpe as date)          as date_dpe,
    try_cast(date_derniere_modification_dpe as date)  as date_modification,
    numero_dpe_remplace,
    methode_application_dpe,
    etiquette_dpe,
    etiquette_ges,
    try_cast(conso_5_usages_par_m2_ep as double)      as conso_ep_m2,
    try_cast(emission_ges_5_usages_par_m2 as double)  as ges_m2,
    try_cast(cout_total_5_usages as double)           as cout_energie_annuel,
    type_batiment,
    try_cast(surface_habitable_logement as double)    as surface_habitable,
    try_cast(annee_construction as integer)           as annee_construction,
    periode_construction,
    type_installation_chauffage,
    type_energie_principale_chauffage,
    identifiant_ban,
    numero_voie_ban,
    nom_rue_ban,
    code_insee_ban,
    nom_commune_ban,
    try_cast(score_ban as double)                     as score_ban,
    statut_geocodage,
    try_cast(split_part(_geopoint, ',', 1) as double) as latitude,
    try_cast(split_part(_geopoint, ',', 2) as double) as longitude,
    _ingere_le
from {{ source('bronze', 'dpe') }}
qualify row_number() over (
    partition by numero_dpe
    order by try_cast(date_derniere_modification_dpe as date) desc nulls last, _ingere_le desc
) = 1
